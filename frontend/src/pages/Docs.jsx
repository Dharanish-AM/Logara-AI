function Docs() {
  return (
    <div className="min-h-screen text-white py-20 px-8 max-w-6xl mx-auto">

      {/* Header */}
      <section className="mb-20 fade-up">

        <div
          className="
            inline-flex
            px-4
            py-2
            rounded-full
            bg-indigo-500/10
            border
            border-indigo-500/20
            text-indigo-400
            mb-6
            backdrop-blur-xl
          "
        >
          Documentation
        </div>

        <h1 className="text-6xl font-black mb-6 tracking-tight leading-tight">
          Build Intelligent

          <span
            className="
              block
              bg-gradient-to-r
              from-indigo-400
              via-sky-400
              to-emerald-400
              bg-clip-text
              text-transparent
            "
          >
            Log Workflows.
          </span>

        </h1>

        <p className="max-w-3xl text-xl text-neutral-400 leading-9 fade-up-delay">
          Logara AI transforms raw infrastructure logs into searchable,
          AI-powered intelligence through semantic retrieval, anomaly
          detection, and local-first processing.
        </p>

      </section>

      {/* Core Capabilities */}
      <section className="mb-24">

        <h2 className="text-4xl font-bold mb-10 fade-up">
          Core Capabilities
        </h2>

        <div className="grid md:grid-cols-2 gap-8">

          <div
            className="
              ui-card
              glass-surface
              rounded-3xl
              p-8
              border
              border-neutral-800
              hover:border-indigo-500/40
            "
          >
            <h3 className="text-xl font-semibold text-indigo-400 mb-4">
              Semantic Search
            </h3>

            <p className="text-neutral-400 leading-8">
              Replace traditional grep workflows with natural language
              search powered by vector embeddings.
            </p>
          </div>

          <div
            className="
              ui-card
              glass-surface
              rounded-3xl
              p-8
              border
              border-neutral-800
              hover:border-sky-500/40
            "
          >
            <h3 className="text-xl font-semibold text-sky-400 mb-4">
              Root Cause Analysis
            </h3>

            <p className="text-neutral-400 leading-8">
              Identify patterns across infrastructure failures and
              automatically summarize probable causes.
            </p>
          </div>

          <div
            className="
              ui-card
              glass-surface
              rounded-3xl
              p-8
              border
              border-neutral-800
              hover:border-emerald-500/40
            "
          >
            <h3 className="text-xl font-semibold text-emerald-400 mb-4">
              Local AI Processing
            </h3>

            <p className="text-neutral-400 leading-8">
              Process sensitive logs locally through Ollama without
              external data exposure.
            </p>
          </div>

          <div
            className="
              ui-card
              glass-surface
              rounded-3xl
              p-8
              border
              border-neutral-800
              hover:border-purple-500/40
            "
          >
            <h3 className="text-xl font-semibold text-purple-400 mb-4">
              Anomaly Correlation
            </h3>

            <p className="text-neutral-400 leading-8">
              Detect unusual activity patterns before reliability issues
              become incidents.
            </p>
          </div>

        </div>

      </section>

      {/* Architecture */}
      <section className="mb-24 fade-up">

        <h2 className="text-4xl font-bold mb-10">
          System Architecture
        </h2>

        <div
          className="
            ui-card
            glass-surface
            rounded-3xl
            p-10
            border
            border-neutral-800
          "
        >

          <div className="space-y-10">

            <div>
              <span className="text-indigo-400 font-semibold text-lg">
                Ingestion Layer
              </span>

              <p className="text-neutral-400 mt-3 leading-8">
                Log Sources → FastAPI Ingestor → Redis Queue
              </p>
            </div>

            <div>
              <span className="text-sky-400 font-semibold text-lg">
                Processing Layer
              </span>

              <p className="text-neutral-400 mt-3 leading-8">
                Redis Queue → Log Processor → Qdrant Vector DB → Ollama
              </p>
            </div>

            <div>
              <span className="text-emerald-400 font-semibold text-lg">
                Interface Layer
              </span>

              <p className="text-neutral-400 mt-3 leading-8">
                GraphQL / REST API → React Dashboard
              </p>
            </div>

          </div>

        </div>

      </section>

      {/* Quick Start */}
      <section className="fade-up">

        <h2 className="text-4xl font-bold mb-8">
          Quick Start
        </h2>

        <div
          className="
            ui-card
            glass-surface
            rounded-3xl
            border
            border-neutral-800
            p-8
            overflow-auto
          "
        >

<pre className="text-sm text-neutral-300 leading-8">{`git clone https://github.com/Dharanish-AM/Logara-AI.git

docker-compose up -d

cd backend
python -m pip install "fastapi[standard]"
python -m fastapi dev main.py

cd frontend
npm install
npm run dev`}</pre>

        </div>

      </section>

    </div>
  );
}

export default Docs;