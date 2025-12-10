import { spawn } from "child_process";

export function runPython(scriptPath, args = []) {
  return new Promise((resolve, reject) => {
    const python = spawn("python", [scriptPath, ...args], {
      cwd: process.cwd(), // root of the project
    });

    let output = "";
    let error = "";

    python.stdout.on("data", (data) => {
      output += data.toString();
    });

    python.stderr.on("data", (data) => {
      error += data.toString();
    });

    python.on("close", (code) => {
      if (code !== 0) {
        reject({ code, error });
      } else {
        resolve(output);
      }
    });
  });
}
