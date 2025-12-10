import dotenv from "dotenv";
dotenv.config();

import { startCoreEngineLoop } from "./coreEngine.js";
import { startMemeEngineLoop } from "./memeEngine.js";

async function main() {
  console.log("========================================");
  console.log("  CRYPTO SIGNAL Pauda ENGINE 5g (core + meme)");
  console.log("========================================");

  startCoreEngineLoop();
  startMemeEngineLoop();
}

main().catch((err) => {
  console.error("[ENGINE] Fatal error:", err);
  process.exit(1);
});
