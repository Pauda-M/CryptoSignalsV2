// backend-engine/src/routes/mlRoutes.js
import express from "express";
import { spawn } from "child_process";
import path from "path";
import fs from "fs";

const router = express.Router();

// ---- FIXED ABSOLUTE PATHS (ADJUST ONLY IF YOU MOVE THE PROJECT) ----
const ML_BASE = path.resolve("C:/CryptoTrader/next_version/crypto-signals/ml");
const PYTHON = path.resolve(ML_BASE, ".venv-ml/Scripts/pythonw.exe");

// ---- LOG HELPER ----
function runPython(scriptName, res) {
  const scriptPath = path.join(ML_BASE, scriptName);

  if (!fs.existsSync(scriptPath)) {
    res.status(500).send(`[ERROR] Missing script: ${scriptPath}`);
    return;
  }

  if (!fs.existsSync(PYTHON)) {
    res.status(500).send(`[ERROR] Python venv missing: ${PYTHON}`);
    return;
  }

  res.write(`[CMD] Using Python: ${PYTHON}\n`);
  res.write(`[CMD] Running script: ${scriptPath}\n\n`);

  const proc = spawn(PYTHON, [scriptPath], {
    shell: false, // no cmd.exe
    cwd: ML_BASE,
  });

  proc.stdout.on("data", (data) => {
    res.write(data.toString());
  });

  proc.stderr.on("data", (data) => {
    res.write(`[ERROR] ${data.toString()}`);
  });

  proc.on("close", (code) => {
    res.write(`\n[CMD] Process exited with code: ${code}\n`);
    res.end();
  });
}

// ---- ROUTES ----
router.get("/build", (req, res) => {
  runPython("build_pumpx_training_data.py", res);
});

router.get("/train", (req, res) => {
  runPython("train_pumpx_xgb.py", res);
});

router.get("/deploy", (req, res) => {
  // This can be whatever you use to "deploy" (load model, validate, etc.)
  runPython("pumpx_predictor.py", res);
});

export default router;
