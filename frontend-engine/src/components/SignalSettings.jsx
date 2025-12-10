import React, { useState, useEffect } from "react";

export default function SignalSettings({ open, onClose, settings, onSave }) {
  const [local, setLocal] = useState(settings);

  useEffect(() => {
    setLocal(settings);
  }, [settings]);

  if (!open) return null;

  const update = (patch) => setLocal((prev) => ({ ...prev, ...patch }));

  const handleSubmit = () => {
    onSave(local);
  };

  return (
    <div className="modal-backdrop">
      <div className="modal">
        <div className="modal-header">
          <div className="modal-title">Signal Settings</div>
          <button className="btn btn-secondary" onClick={onClose}>
            ✕
          </button>
        </div>

        <div className="modal-field">
          <label className="modal-label">Minimum confidence (%)</label>
          <input
            type="number"
            min="0"
            max="100"
            className="modal-input"
            value={Math.round((local.minConfidence ?? 0.8) * 100)}
            onChange={(e) =>
              update({
                minConfidence: Math.max(
                  0,
                  Math.min(1, Number(e.target.value || 0) / 100)
                )
              })
            }
          />
        </div>

        <div className="modal-field">
          <label className="modal-label">Maximum rows</label>
          <input
            type="number"
            min="10"
            max="1000"
            className="modal-input"
            value={local.maxRows ?? 100}
            onChange={(e) =>
              update({
                maxRows: Math.max(10, Math.min(1000, Number(e.target.value) || 10))
              })
            }
          />
        </div>

        <div className="modal-footer">
          <button className="btn btn-secondary" onClick={onClose}>
            Cancel
          </button>
          <button className="btn btn-primary" onClick={handleSubmit}>
            Save
          </button>
        </div>
      </div>
    </div>
  );
}
