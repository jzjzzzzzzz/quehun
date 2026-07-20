# Optional CNN training path

The live analyzer uses `cv.template_classifier.TemplateTileClassifier` and does not require Torch.
This directory preserves an optional convolutional model and training experiment for future
classifier work.

Install the separate training dependencies before importing this package:

```bash
python -m pip install -r requirements-training.txt
```

Tracked model weights are research artifacts and are not loaded by the default runtime. Changes to
weights or datasets should document training inputs, class ordering, evaluation results, and file
provenance in the pull request.

The dataset used by the experiment is described in [`dataset/README.md`](../dataset/README.md) and
retains its own [`dataset/LICENSE`](../dataset/LICENSE).
