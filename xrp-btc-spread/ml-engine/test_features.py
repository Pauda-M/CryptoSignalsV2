from feature_builder.feature_builder_v2 import build_feature_matrix
import numpy as np

ts, X, y, y_dir = build_feature_matrix()

print("X shape =", X.shape)
print("y shape =", y.shape)
print("y_dir shape =", y_dir.shape)

print("Checking X for NaN/Inf...")
print("NaN count:", np.isnan(X).sum())
print("Inf count:", np.isinf(X).sum())

print("Checking y for NaN/Inf...")
print("NaN count:", np.isnan(y).sum())
print("Inf count:", np.isinf(y).sum())

print("Checking y_dir for NaN/Inf...")
print("NaN count:", np.isnan(y_dir).sum())
print("Inf count:", np.isinf(y_dir).sum())

print("DONE")
