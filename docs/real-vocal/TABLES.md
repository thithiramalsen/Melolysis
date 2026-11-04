# Measured real-vocal tables

Generated from immutable completed runs; A1 and A2 are scored separately. No best-edition selection.

## development

| System | Edition | Onset P/R/F1 | Onset + pitch P/R/F1 | Full note P/R/F1 | Onset/offset MAE (ms) |
|---|---|---|---|---|---|
| pyin-baseline | A1 | 0.7781 / 0.5414 / 0.6340 | 0.7076 / 0.4934 / 0.5772 | 0.5562 / 0.3941 / 0.4577 | 21.0 / 76.1 |
| pyin-baseline | A2 | 0.7071 / 0.5762 / 0.6349 | 0.6087 / 0.4963 / 0.5467 | 0.4519 / 0.3681 / 0.4056 | 19.2 / 80.8 |
| torchcrepe-tiny-events | A1 | 0.6998 / 0.5614 / 0.6179 | 0.5275 / 0.4332 / 0.4720 | 0.3005 / 0.2557 / 0.2747 | 20.7 / 126.2 |
| torchcrepe-tiny-events | A2 | 0.6808 / 0.6336 / 0.6537 | 0.5271 / 0.4928 / 0.5072 | 0.3464 / 0.3244 / 0.3338 | 21.0 / 133.8 |
| game-small | A1 | 0.7830 / 0.6251 / 0.6906 | 0.7013 / 0.5620 / 0.6196 | 0.4037 / 0.3202 / 0.3549 | 12.3 / 87.1 |
| game-small | A2 | 0.8455 / 0.8062 / 0.8250 | 0.7915 / 0.7554 / 0.7726 | 0.5152 / 0.4923 / 0.5032 | 14.7 / 67.0 |
| game-tail-refined | A1 | 0.7830 / 0.6251 / 0.6906 | 0.7013 / 0.5620 / 0.6196 | 0.4873 / 0.3889 / 0.4295 | 12.3 / 76.9 |
| game-tail-refined | A2 | 0.8455 / 0.8062 / 0.8250 | 0.7915 / 0.7554 / 0.7726 | 0.6505 / 0.6208 / 0.6350 | 14.7 / 54.9 |

Timing errors are conditional on onset+pitch matches. Macro averages give each excerpt equal weight.

| Track | Human note counts A1/A2 | pYIN full F1 A1/A2 | CREPE Tiny full F1 A1/A2 | GAME full F1 A1/A2 | GAME refined full F1 A1/A2 |
|---|---:|---:|---:|---:|---:|
| [vocadito_1](vocadito_1.png) | 59 / 64 | 0.6429 / 0.5128 | 0.5088 / 0.4874 | 0.3306 / 0.5079 | 0.4463 / 0.6667 |
| [vocadito_2](vocadito_2.png) | 76 / 63 | 0.3780 / 0.2982 | 0.2416 / 0.2647 | 0.3308 / 0.4833 | 0.3459 / 0.4833 |
| [vocadito_4](vocadito_4.png) | 69 / 51 | 0.3486 / 0.4176 | 0.2712 / 0.4000 | 0.3793 / 0.4286 | 0.5000 / 0.7143 |
| [vocadito_5](vocadito_5.png) | 96 / 72 | 0.4615 / 0.3939 | 0.0774 / 0.1832 | 0.3787 / 0.5931 | 0.4260 / 0.6759 |

| System | Cold wall seconds: mean / range | Peak sampled summed RSS (MiB) |
|---|---:|---:|
| pyin-baseline | 14.63 / 10.23–18.00 | 281.0 |
| torchcrepe-tiny-events | 10.07 / 8.49–11.59 | 416.7 |
| game-small | 28.39 / 22.03–33.18 | 800.8 |
| game-tail-refined | 1.55 / 1.44–1.73 | 108.6 |

Refined row measures refinement only, excluding parent inference; add GAME cost for end-to-end use.
RSS is sampled process-tree resident memory, not exclusive RAM, allocation peaks, or GPU memory.

## heldout

| System | Edition | Onset P/R/F1 | Onset + pitch P/R/F1 | Full note P/R/F1 | Onset/offset MAE (ms) |
|---|---|---|---|---|---|
| pyin-baseline | A1 | 0.7671 / 0.5806 / 0.6590 | 0.6611 / 0.5018 / 0.5689 | 0.4532 / 0.3401 / 0.3875 | 18.9 / 70.8 |
| pyin-baseline | A2 | 0.6929 / 0.6666 / 0.6789 | 0.5732 / 0.5526 / 0.5622 | 0.4034 / 0.3896 / 0.3960 | 18.3 / 81.2 |
| torchcrepe-tiny-events | A1 | 0.7638 / 0.5679 / 0.6509 | 0.5480 / 0.4095 / 0.4684 | 0.2889 / 0.2160 / 0.2470 | 21.9 / 112.4 |
| torchcrepe-tiny-events | A2 | 0.7194 / 0.6745 / 0.6951 | 0.5210 / 0.4843 / 0.5012 | 0.3005 / 0.2818 / 0.2904 | 19.6 / 111.8 |
| game-small | A1 | 0.8572 / 0.6826 / 0.7580 | 0.7237 / 0.5800 / 0.6423 | 0.3514 / 0.2818 / 0.3120 | 10.5 / 96.3 |
| game-small | A2 | 0.8690 / 0.8741 / 0.8715 | 0.8148 / 0.8196 / 0.8172 | 0.4525 / 0.4549 / 0.4537 | 11.3 / 73.5 |
| game-tail-refined | A1 | 0.8572 / 0.6826 / 0.7580 | 0.7237 / 0.5800 / 0.6423 | 0.4334 / 0.3444 / 0.3829 | 10.5 / 82.3 |
| game-tail-refined | A2 | 0.8690 / 0.8741 / 0.8715 | 0.8148 / 0.8196 / 0.8172 | 0.5321 / 0.5346 / 0.5333 | 11.3 / 62.2 |

Timing errors are conditional on onset+pitch matches. Macro averages give each excerpt equal weight.

| Track | Human note counts A1/A2 | pYIN full F1 A1/A2 | CREPE Tiny full F1 A1/A2 | GAME full F1 A1/A2 | GAME refined full F1 A1/A2 |
|---|---:|---:|---:|---:|---:|
| [vocadito_6](vocadito_6.png) | 73 / 50 | 0.3871 / 0.4554 | 0.2362 / 0.2692 | 0.2439 / 0.4000 | 0.3089 / 0.4800 |
| [vocadito_7](vocadito_7.png) | 47 / 42 | 0.3636 / 0.4819 | 0.3294 / 0.4500 | 0.3556 / 0.4000 | 0.3556 / 0.4235 |
| [vocadito_10](vocadito_10.png) | 35 / 27 | 0.3448 / 0.2400 | 0.2000 / 0.1923 | 0.2903 / 0.4815 | 0.4194 / 0.6296 |
| [vocadito_11](vocadito_11.png) | 37 / 30 | 0.4545 / 0.4068 | 0.2222 / 0.2500 | 0.3582 / 0.5333 | 0.4478 / 0.6000 |

| System | Cold wall seconds: mean / range | Peak sampled summed RSS (MiB) |
|---|---:|---:|
| pyin-baseline | 9.51 / 6.29–13.10 | 279.5 |
| torchcrepe-tiny-events | 7.49 / 5.95–8.91 | 409.6 |
| game-small | 20.75 / 15.84–26.58 | 804.6 |
| game-tail-refined | 1.40 / 1.37–1.47 | 107.3 |

Refined row measures refinement only, excluding parent inference; add GAME cost for end-to-end use.
RSS is sampled process-tree resident memory, not exclusive RAM, allocation peaks, or GPU memory.

## Reference disagreement

| Track | A1 vs A2 onset + pitch F1 | A1 vs A2 full F1 |
|---|---:|---:|
| vocadito_1 | 0.8618 | 0.7317 |
| vocadito_2 | 0.6906 | 0.5324 |
| vocadito_4 | 0.7000 | 0.6167 |
| vocadito_5 | 0.5952 | 0.5000 |
| vocadito_6 | 0.6667 | 0.4553 |
| vocadito_7 | 0.6966 | 0.5169 |
| vocadito_10 | 0.6774 | 0.6452 |
| vocadito_11 | 0.7463 | 0.7164 |
