import React from "react";
import { Link, useNavigate } from "react-router-dom";

const Navbar = () => {
  const navigate = useNavigate();

  return (
    <nav
      className="
        sticky
        top-0
        z-50
        flex
        items-center
        justify-between
        px-6
        md:px-10
        py-5
        text-white
        border-b
        border-white/5
        backdrop-blur-xl
        bg-black/35
      "
    >
      {/* Logo */}
      <div className="flex items-center gap-3 select-none">
        <div
          className="
            w-10
            h-10
            rounded-xl
            bg-gradient-to-br
            from-indigo-500
            to-violet-600
            flex
            items-center
            justify-center
            font-bold
            shadow-lg
            shadow-indigo-500/20
            transition
            duration-300
            hover:scale-105
          "
        >
          L
        </div>

        <h1
          className="
            text-2xl
            font-bold
            tracking-tight
          "
        >
          Logara AI
        </h1>
      </div>

      {/* Navigation */}
      <div
        className="
          hidden
          md:flex
          items-center
          gap-8
          text-sm
          font-medium
          text-neutral-400
        "
      >
        <Link
          to="/#features"
          className="
            relative
            hover:text-white
            transition
            duration-300
            after:absolute
            after:left-0
            after:-bottom-1
            after:h-[2px]
            after:w-0
            after:bg-indigo-400
            after:transition-all
            after:duration-300
            hover:after:w-full
          "
        >
          Features
        </Link>

        <Link
          to="/#architecture"
          className="
            relative
            hover:text-white
            transition
            duration-300
            after:absolute
            after:left-0
            after:-bottom-1
            after:h-[2px]
            after:w-0
            after:bg-indigo-400
            after:transition-all
            after:duration-300
            hover:after:w-full
          "
        >
          Architecture
        </Link>

        <Link
          to="/docs"
          className="
            relative
            hover:text-white
            transition
            duration-300
            after:absolute
            after:left-0
            after:-bottom-1
            after:h-[2px]
            after:w-0
            after:bg-indigo-400
            after:transition-all
            after:duration-300
            hover:after:w-full
          "
        >
          Docs
        </Link>

        <a
          href="https://github.com/Dharanish-AM/Logara-AI"
          target="_blank"
          rel="noreferrer"
          className="
            relative
            hover:text-white
            transition
            duration-300
            after:absolute
            after:left-0
            after:-bottom-1
            after:h-[2px]
            after:w-0
            after:bg-indigo-400
            after:transition-all
            after:duration-300
            hover:after:w-full
          "
        >
          GitHub
        </a>
      </div>

      {/* CTA */}
      <button
        onClick={() => navigate("/dashboard")}
        className="
          ui-button
          px-6
          py-3
          rounded-2xl
          bg-white
          text-black
          font-semibold
          hover:bg-neutral-200
          active:scale-95
        "
      >
        Get Started
      </button>
    </nav>
  );
};

export default Navbar;