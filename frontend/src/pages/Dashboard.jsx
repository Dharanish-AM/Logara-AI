function Dashboard() {
  return (
    <div className="min-h-screen text-white py-12">

      {/* Header */}
      <div className="mb-12 fade-up">
        <h1 className="text-5xl font-black tracking-tight">
          AI Log Dashboard
        </h1>

        <p className="text-neutral-400 mt-4 max-w-2xl">
          Monitor anomalies, analyze logs, and discover infrastructure insights.
        </p>
      </div>

      {/* Stats */}
      <div className="grid md:grid-cols-4 gap-6 mb-16">

        <div
          className="
            ui-card
            group
            p-6
            rounded-3xl
            border
            border-neutral-800
            bg-neutral-950/80
            backdrop-blur-xl
            hover:border-indigo-500/40
          "
        >
          <h2 className="text-neutral-400 text-sm">
            Logs Processed
          </h2>

          <p
            className="
              text-4xl
              font-black
              mt-3
              transition-all
              duration-300
              group-hover:text-indigo-300
              group-hover:scale-105
            "
          >
            24.5K
          </p>

          <div
            className="
              mt-5
              h-[2px]
              w-0
              bg-indigo-400
              transition-all
              duration-500
              group-hover:w-full
            "
          />
        </div>

        <div
          className="
            ui-card
            group
            p-6
            rounded-3xl
            border
            border-neutral-800
            bg-neutral-950/80
            backdrop-blur-xl
            hover:border-rose-500/40
          "
        >
          <h2 className="text-neutral-400 text-sm">
            Anomalies
          </h2>

          <p
            className="
              text-4xl
              font-black
              mt-3
              text-rose-400
              transition-all
              duration-300
              group-hover:scale-110
            "
          >
            12
          </p>

          <div
            className="
              mt-5
              h-[2px]
              w-0
              bg-rose-400
              transition-all
              duration-500
              group-hover:w-full
            "
          />
        </div>

        <div
          className="
            ui-card
            group
            p-6
            rounded-3xl
            border
            border-neutral-800
            bg-neutral-950/80
            backdrop-blur-xl
            hover:border-sky-500/40
          "
        >
          <h2 className="text-neutral-400 text-sm">
            Active Services
          </h2>

          <p
            className="
              text-4xl
              font-black
              mt-3
              text-sky-400
              transition-all
              duration-300
              group-hover:translate-x-1
            "
          >
            8
          </p>

          <div
            className="
              mt-5
              h-[2px]
              w-0
              bg-sky-400
              transition-all
              duration-500
              group-hover:w-full
            "
          />
        </div>

        <div
          className="
            ui-card
            group
            p-6
            rounded-3xl
            border
            border-neutral-800
            bg-neutral-950/80
            backdrop-blur-xl
            hover:border-emerald-500/40
          "
        >
          <h2 className="text-neutral-400 text-sm">
            AI Insights
          </h2>

          <p
            className="
              text-4xl
              font-black
              mt-3
              text-emerald-400
              transition-all
              duration-300
              group-hover:scale-110
            "
          >
            34
          </p>

          <div
            className="
              mt-5
              h-[2px]
              w-0
              bg-emerald-400
              transition-all
              duration-500
              group-hover:w-full
            "
          />
        </div>

      </div>

      {/* AI Insight */}
      <div
        className="
          ui-card
          p-8
          rounded-3xl
          border
          border-indigo-900/40
          bg-neutral-950/80
          backdrop-blur-xl
          mb-12
          transition-all
          duration-300
          hover:border-indigo-500/40
          hover:shadow-[0_0_40px_rgba(99,102,241,0.15)]
        "
      >

        <h2 className="text-2xl font-bold text-indigo-400 mb-4">
          AI Summary
        </h2>

        <p className="text-neutral-400 leading-8">
          Elevated database timeout errors detected after deployment v2.1.
          Similar patterns occurred 3 days ago and correlate with Redis
          latency spikes.
        </p>

      </div>

      {/* Recent Logs */}
      <div
        className="
          ui-card
          p-8
          rounded-3xl
          border
          border-neutral-800
          bg-neutral-950/80
          backdrop-blur-xl
        "
      >

        <h2 className="text-2xl font-bold mb-6">
          Recent Logs
        </h2>

        <div className="space-y-4">

          <div
            className="
              bg-black/40
              border
              border-white/5
              rounded-2xl
              px-5
              py-4
              transition-all
              duration-300
              hover:border-rose-500/30
              hover:bg-rose-500/5
              hover:translate-x-1
            "
          >
            ERROR: Database timeout detected
          </div>

          <div
            className="
              bg-black/40
              border
              border-white/5
              rounded-2xl
              px-5
              py-4
              transition-all
              duration-300
              hover:border-amber-500/30
              hover:bg-amber-500/5
              hover:translate-x-1
            "
          >
            WARNING: Redis queue delay increased
          </div>

          <div
            className="
              bg-black/40
              border
              border-white/5
              rounded-2xl
              px-5
              py-4
              transition-all
              duration-300
              hover:border-emerald-500/30
              hover:bg-emerald-500/5
              hover:translate-x-1
            "
          >
            INFO: Service health restored
          </div>

        </div>

      </div>

    </div>
  );
}

export default Dashboard;