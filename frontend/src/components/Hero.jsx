import { useNavigate } from "react-router-dom";

function Hero() {
  const navigate = useNavigate();

  return (
    <section
      className="
        relative
        overflow-hidden
        min-h-[78vh]
        flex
        items-center
        text-white
        py-24
      "
    >

      {/* Background Glow */}
      <div
        className="
          absolute
          top-[-120px]
          left-1/2
          -translate-x-1/2
          w-[700px]
          h-[700px]
          rounded-full
          bg-indigo-500/10
          blur-3xl
          pointer-events-none
        "
      />

      <div className="relative z-10 max-w-6xl mx-auto text-center">

        {/* Badge */}
        <div
          className="
            inline-flex
            items-center
            gap-2
            px-4
            py-2
            rounded-full
            border
            border-indigo-500/20
            bg-indigo-500/10
            text-indigo-300
            text-sm
            mb-8
            backdrop-blur-xl
            fade-up
          "
        >
          AI-Powered Infrastructure Intelligence
        </div>

        {/* Heading */}
        <h1
  className="
    text-6xl
    md:text-7xl
    font-black
    tracking-tight
    leading-[1.05]
    max-w-5xl
    mb-8
    mx-auto
    fade-up
  "
>
  Log Intelligence.

  <span
    className="
      block
      bg-gradient-to-r
      from-indigo-400
      via-sky-400
      to-emerald-400
      bg-clip-text
      text-transparent
      mt-2
    "
  >
    Powered by AI.
  </span>

</h1>

        {/* Description */}
        <p
        className="
        max-w-3xl
        text-lg
        md:text-xl
        text-neutral-400
        leading-9
        mb-12
        text-center
        mx-auto
        fade-up-delay
        "
      >
          Logara AI helps engineering teams monitor anomalies,
          analyze infrastructure logs, and uncover operational
          insights through semantic search and AI-powered workflows.
        </p>

        {/* Buttons */}
        <div className="flex flex-wrap justify-center items-center gap-5 fade-up-delay">

          <button
            onClick={() => navigate("/dashboard")}
            className="
              px-7
              py-4
              rounded-2xl
              bg-white
              text-black
              font-semibold
              transition-all
              duration-300
              hover:-translate-y-1
              hover:bg-indigo-500
              hover:text-white
              hover:shadow-[0_0_35px_rgba(99,102,241,0.45)]
              active:scale-95
            "
          >
            Deploy Locally →
          </button>

          <button
            onClick={() => navigate("/docs")}
            className="
              px-7
              py-4
              rounded-2xl
              border
              border-white/10
              bg-white/5
              backdrop-blur-xl
              text-white
              font-semibold
              transition-all
              duration-300
              hover:-translate-y-1
              hover:border-indigo-500/30
              hover:bg-indigo-500/10
            "
          >
            Read the Docs
          </button>

        </div>

        {/* Metrics */}
        <div className="grid md:grid-cols-3 gap-6 mt-14">

          <div
            className="
              ui-card
              glass-surface
              p-6
              rounded-3xl
              border
              border-neutral-800
            "
          >
            <p className="text-sm text-neutral-500 mb-2">
              Logs Indexed
            </p>

            <h3 className="text-4xl font-black text-indigo-300">
              24M+
            </h3>
          </div>

          <div
            className="
              ui-card
              glass-surface
              p-6
              rounded-3xl
              border
              border-neutral-800
            "
          >
            <p className="text-sm text-neutral-500 mb-2">
              AI Insights Generated
            </p>

            <h3 className="text-4xl font-black text-sky-300">
              180K+
            </h3>
          </div>

          <div
            className="
              ui-card
              glass-surface
              p-6
              rounded-3xl
              border
              border-neutral-800
            "
          >
            <p className="text-sm text-neutral-500 mb-2">
              Infrastructure Events
            </p>

            <h3 className="text-4xl font-black text-emerald-300">
              Real-Time
            </h3>
          </div>

        </div>

      </div>

    </section>
  );
}

export default Hero;