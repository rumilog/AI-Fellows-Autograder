#!/usr/bin/env bash

apt-get install python3.10
python3.10 -m pip install torch==2.3.1 torchvision==0.18.1 torchaudio==2.3.1 --index-url https://download.pytorch.org/whl/cu121
# python3.10 -m pip install numpy==1.26.4
# python3.10 -m pip matplotlib==3.7.1 pandas==2.1.4 scikit-learn==1.3.2