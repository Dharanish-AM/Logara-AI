import asyncio
import json
import logging
import uuid
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime
import time

from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
try:
    from qdrant_client.models import PointStruct
except ImportError:
    from qdrant_client.http.models import PointStruct

logger = logging.getLogger(__name__)


@dataclass
class ProcessedLog:
    id: str
    timestamp: str
    level: str
    message: str
    service_id: str
    vector: List[float]
    metadata: Dict[str, Any]
    parser_type: Optional[str] = None
    cluster_id: Optional[str] = None
    processing_time_ms: float = 0.0


class BatchLogProcessor:
    def __init__(
        self,
        batch_size: int = 32,
        max_batch_wait_ms: int = 100,
        embedding_model: Optional[SentenceTransformer] = None,
        qdrant_client: Optional[QdrantClient] = None,
    ):
        self.batch_size = batch_size
        self.max_batch_wait_ms = max_batch_wait_ms
        self.embedding_model = embedding_model
        self.qdrant_client = qdrant_client
        self.pending_logs: List[Dict[str, Any]] = []
        self.pending_since = time.time()
        self.embedding_cache: Dict[str, List[float]] = {}
        self.cache_size = 1000

    async def add_log(self, log_data: Dict[str, Any]) -> None:
        self.pending_logs.append(log_data)

        if len(self.pending_logs) >= self.batch_size:
            await self.flush_batch()
        else:
            elapsed_ms = (time.time() - self.pending_since) * 1000
            if elapsed_ms > self.max_batch_wait_ms and self.pending_logs:
                await self.flush_batch()

    async def flush_batch(self) -> List[ProcessedLog]:
        if not self.pending_logs:
            return []

        batch = self.pending_logs[: self.batch_size]
        self.pending_logs = self.pending_logs[self.batch_size :]

        start_time = time.time()

        try:
            processed_logs = await self._process_batch(batch)
            processing_time = (time.time() - start_time) * 1000

            logger.info(
                f"Batch processed successfully | "
                f"batch_size={len(batch)} | "
                f"processing_time_ms={processing_time:.2f} | "
                f"avg_per_log_ms={processing_time / len(batch):.2f}"
            )

            return processed_logs

        except Exception as e:
            logger.error(f"Error processing batch: {str(e)}")
            self.pending_logs.extend(batch)
            return []

    async def _process_batch(
        self, batch: List[Dict[str, Any]]
    ) -> List[ProcessedLog]:
        messages = [
            log.get("parsed", {}).get("message", "") or log.get("message", "")
            for log in batch
        ]

        embeddings = await self._get_embeddings(messages)

        processed_logs = []
        for i, log_data in enumerate(batch):
            try:
                processed_log = ProcessedLog(
                    id=str(uuid.uuid4()),
                    timestamp=log_data.get("parsed", {}).get(
                        "timestamp", datetime.now().isoformat()
                    ),
                    level=log_data.get("parsed", {}).get("level", "INFO"),
                    message=log_data.get("parsed", {}).get(
                        "message", log_data.get("message", "")
                    ),
                    service_id=log_data.get("metadata", {}).get(
                        "service", "unknown"
                    ),
                    vector=embeddings[i] if i < len(embeddings) else [],
                    metadata=log_data.get("metadata", {}),
                    parser_type=log_data.get("parser_type"),
                    processing_time_ms=(time.time() - time.time()) * 1000,
                )
                processed_logs.append(processed_log)
            except Exception as e:
                logger.error(f"Error processing individual log: {str(e)}")
                continue

        return processed_logs

    async def _get_embeddings(self, messages: List[str]) -> List[List[float]]:
        if not self.embedding_model:
            return [[] for _ in messages]

        uncached_messages = []
        uncached_indices = []

        for i, msg in enumerate(messages):
            msg_hash = hash(msg) % (2**31)
            if msg_hash in self.embedding_cache:
                uncached_messages.append(None)
            else:
                uncached_messages.append(msg)
                uncached_indices.append((i, msg_hash, msg))

        if uncached_messages and uncached_indices:
            new_messages = [m for m, _ in [(msg, i) for i, msg in enumerate(messages) if msg not in [x[2] for x in uncached_indices]]]

            loop = asyncio.get_event_loop()
            embeddings_result = await loop.run_in_executor(
                None,
                lambda: self.embedding_model.encode(new_messages, batch_size=32),
            )

            for (idx, msg_hash, msg), embedding in zip(
                uncached_indices, embeddings_result
            ):
                self.embedding_cache[msg_hash] = embedding.tolist()
                if len(self.embedding_cache) > self.cache_size:
                    oldest_key = next(iter(self.embedding_cache))
                    del self.embedding_cache[oldest_key]

        result = []
        for msg in messages:
            msg_hash = hash(msg) % (2**31)
            result.append(self.embedding_cache.get(msg_hash, []))

        return result

    async def store_logs(
        self, processed_logs: List[ProcessedLog], collection_name: str
    ) -> bool:
        if not self.qdrant_client or not processed_logs:
            return False

        try:
            points = [
                PointStruct(
                    id=log.id,
                    vector=log.vector,
                    payload={
                        "timestamp": log.timestamp,
                        "level": log.level,
                        "message": log.message,
                        "service_id": log.service_id,
                        "metadata": log.metadata,
                        "parser_type": log.parser_type,
                        "cluster_id": log.cluster_id,
                    },
                )
                for log in processed_logs
            ]

            self.qdrant_client.upsert(
                collection_name=collection_name,
                points=points,
            )

            logger.info(
                f"Batch stored to Qdrant | "
                f"logs_stored={len(processed_logs)} | "
                f"collection={collection_name}"
            )

            return True

        except Exception as e:
            logger.error(f"Error storing batch to Qdrant: {str(e)}")
            return False


class ParallelLogProcessor:
    def __init__(
        self,
        num_workers: int = 4,
        batch_size: int = 32,
        embedding_model: Optional[SentenceTransformer] = None,
        qdrant_client: Optional[QdrantClient] = None,
    ):
        self.num_workers = num_workers
        self.batch_size = batch_size
        self.embedding_model = embedding_model
        self.qdrant_client = qdrant_client
        self.workers: List[BatchLogProcessor] = [
            BatchLogProcessor(
                batch_size=batch_size,
                embedding_model=embedding_model,
                qdrant_client=qdrant_client,
            )
            for _ in range(num_workers)
        ]
        self.current_worker_idx = 0

    async def process_log(self, log_data: Dict[str, Any]) -> None:
        worker = self.workers[self.current_worker_idx]
        self.current_worker_idx = (self.current_worker_idx + 1) % self.num_workers

        await worker.add_log(log_data)

    async def flush_all(self) -> List[ProcessedLog]:
        tasks = [worker.flush_batch() for worker in self.workers]
        results = await asyncio.gather(*tasks, return_exceptions=False)

        all_logs = []
        for result in results:
            if isinstance(result, list):
                all_logs.extend(result)

        return all_logs

    async def get_statistics(self) -> Dict[str, Any]:
        total_pending = sum(len(w.pending_logs) for w in self.workers)
        total_cached = sum(len(w.embedding_cache) for w in self.workers)

        return {
            "num_workers": self.num_workers,
            "batch_size": self.batch_size,
            "total_pending_logs": total_pending,
            "total_cached_embeddings": total_cached,
            "worker_details": [
                {
                    "worker_id": i,
                    "pending_logs": len(w.pending_logs),
                    "cached_embeddings": len(w.embedding_cache),
                }
                for i, w in enumerate(self.workers)
            ],
        }
