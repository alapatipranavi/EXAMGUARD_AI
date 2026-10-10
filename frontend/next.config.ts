import type { NextConfig } from "next";
import { PHASE_DEVELOPMENT_SERVER, PHASE_PRODUCTION_BUILD } from "next/constants";

export default function config(phase: string): NextConfig {
  const isDev = phase === PHASE_DEVELOPMENT_SERVER;
  const isBuild = phase === PHASE_PRODUCTION_BUILD || process.argv.includes("build");

  return {
    reactStrictMode: true,
    distDir: isBuild ? ".next_build" : ".next",
  };
}
