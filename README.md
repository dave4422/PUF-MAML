# Repository for DAMI II Project Stockholm University  HT2019
David Mildenberger

## Usage:
Generate challenges and prepare data sets:
```
python gen_ro_data.py
```
```
python -m experiments.maml2 --dataset roPUF --order 2 --n 20 --k 1 --q 1 --meta-batch-size 75 --inner-train-steps 50 --inner-val-steps 10 --inner-lr 0.01 --eval-batches 5 --epoch-len 10 --test-board D070802 --challenge-size 64 --load-indexed False --epochs 1
```
## Experiments:
Results from paper are in results directory
64 bit model:
roPUF-order=2-n=10-k=1-metabatch=60-trainsteps=40val-steps=10.zip

128 bit model:
roPUF_order=2_n=90_k=1_metabatch=75_train_steps=50_val_steps=10.zip
## Credits
Implementation based on 
https://github.com/oscarknagg/few-shot/
