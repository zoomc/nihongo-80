# 题目目标 / 语境分离报告

- 生成脚本：`scripts/audit_questions.py`（契约 1.1，确定性规则）
- 题目数：395｜target 非空：395｜fallback：176
- 能力分布：meaning=5、reading=38、listening=21、usage=226、production=105
- 校验：target+context == knowledge_ids 全部通过；Q0001 target = `G0001`

## 规则

R1 例句完全一致 → 语法 usage；R2 等于词 surface/kana → 词（listen=listening，问中文=meaning，问读音=reading）；R3 汉字音读/训读且问读音 → reading；R4 命中 pattern、R5 命中例句片段 → 语法 usage；R6 产出题 → 首个语法 production；R7 无命中 → knowledge_ids[0]（fallback）。

## fallback 清单（需人工复核）

| 题目 | 类型 | 回退目标 | 能力 | 原 knowledge_ids |
|---|---|---|---|---|
| Q0004 | read | G0001 | reading | G0001、V0078、V0001 |
| Q0005 | reorder | G0001 | usage | G0001、V0001、V0078 |
| Q0012 | listen | G0005 | listening | G0005、V0028、K0021 |
| Q0013 | read | G0005 | reading | G0005、V0028、V0080、K0021 |
| Q0014 | reorder | G0005 | usage | G0005、V0019 |
| Q0015 | error_correct | G0005 | usage | G0005、V0080 |
| Q0022 | read | G0003 | reading | G0003、G0001、V0031、V0032、V0023 |
| Q0023 | reorder | G0003 | usage | G0003、V0025、V0037 |
| Q0031 | read | G0004 | reading | G0004、V0001、V0078 |
| Q0032 | reorder | G0006 | usage | G0006、V0001、V0080 |
| Q0040 | read | G0007 | reading | G0007、V0134、V0056、V0055 |
| Q0041 | reorder | G0007 | usage | G0007、V0134、V0056 |
| Q0048 | listen | G0008 | listening | G0008、V0053、V0102、K0004、K0060 |
| Q0049 | read | G0009 | reading | G0009、G0008、V0015、V0119、V0051 |
| Q0050 | reorder | G0008 | usage | G0008、V0051、V0101 |
| Q0058 | read | G0010 | reading | G0010、G0011、V0060、V0044、V0082 |
| Q0059 | reorder | G0011 | usage | G0011、V0039、V0103 |
| Q0067 | read | G0012 | reading | G0012、G0013、V0076、V0041、V0039、V0036 |
| Q0068 | reorder | G0012 | usage | G0012、V0076、V0099、V0105 |
| Q0076 | read | G0014 | reading | G0014、V0045、V0098、V0109 |
| Q0077 | reorder | G0014 | usage | G0014、V0045、V0098、V0109 |
| Q0085 | read | G0015 | reading | G0015、G0016、V0080、V0125、V0136 |
| Q0086 | reorder | G0015 | usage | G0015、V0080、V0125 |
| Q0093 | listen | G0017 | listening | G0017、V0133、V0023 |
| Q0094 | read | G0017 | reading | G0017、V0025、V0133 |
| Q0095 | reorder | G0017 | usage | G0017、V0080、V0125 |
| Q0101 | fill | G0019 | usage | G0019、V0029、V0039、V0103、K0062 |
| Q0103 | read | G0019 | reading | G0019、G0020、V0119、V0051、V0101 |
| Q0104 | reorder | G0020 | usage | G0020、G0019、V0051、V0101、V0103 |
| Q0109 | mcq | G0024 | usage | G0024、V0081、V0114、K0056、K0055 |
| Q0112 | read | G0024 | reading | G0024、G0007、V0124、V0081、V0114 |
| Q0113 | reorder | G0024 | usage | G0024、V0081、V0114 |
| Q0119 | fill | G0037 | usage | G0037、V0096、V0103 |
| Q0121 | read | G0037 | reading | G0037、V0147、V0096、V0118、V0103 |
| Q0122 | reorder | G0036 | usage | G0036、V0024、V0096 |
| Q0127 | mcq | G0050 | usage | G0050、V0079、V0078、V0080、V0113、K0057、K0065 |
| Q0128 | fill | G0049 | usage | G0049、V0096、V0118 |
| Q0130 | read | G0049 | reading | G0049、V0096、V0118、V0038、V0122 |
| Q0131 | reorder | G0050 | usage | G0050、V0079、V0078、V0080、V0113 |
| Q0136 | mcq | G0052 | usage | G0052、V0076、V0081、V0121 |
| Q0139 | read | G0052 | reading | G0052、V0001、V0076、V0081、V0121、V0007 |
| Q0140 | reorder | G0052 | usage | G0052、V0001、V0076、V0081、V0121 |
| Q0141 | error_correct | G0052 | usage | G0052、V0076、V0121 |
| Q0145 | mcq | G0043 | usage | G0043、V0096、V0118 |
| Q0149 | reorder | G0043 | usage | G0043、V0096、V0118 |
| Q0150 | error_correct | G0043 | usage | G0043、V0130 |
| Q0158 | reorder | G0046 | usage | G0046、V0083、V0107 |
| Q0166 | read | G0053 | reading | G0053、V0125、V0130 |
| Q0167 | reorder | G0053 | usage | G0053、V0074、V0122 |
| Q0175 | read | G0055 | reading | G0055、V0077、V0081、V0114 |
| Q0176 | reorder | G0055 | usage | G0055、V0001、V0081、V0132 |
| Q0184 | mcq | V0004 | usage | V0004、V0006、V0005 |
| Q0185 | error_correct | V0003 | usage | V0003、V0001、G0001 |
| Q0186 | translate | V0005 | production | V0005 |
| Q0190 | fill | V0007 | usage | V0007 |
| Q0193 | reorder | G0002 | usage | G0002、V0003 |
| Q0198 | read | K0006 | reading | K0006、K0007、V0023 |
| Q0200 | error_correct | G0003 | usage | G0003、V0001 |
| Q0203 | listen | V0020 | listening | V0020 |
| Q0204 | reorder | G0001 | usage | G0001、V0001 |
| Q0206 | dialogue | V0020 | production | V0020、V0021、V0007 |
| Q0211 | error_correct | V0029 | reading | V0029、K0001 |
| Q0212 | free_production | V0029 | production | V0029、V0026、V0027 |
| Q0220 | mcq | V0241 | usage | V0241、V0240、V0154、V0155、G0007 |
| Q0221 | mcq | V0234 | usage | V0234、V0237、V0238、V0231、V0188、V0054、K0118、K0095 |
| Q0222 | mcq | V0232 | usage | V0232、V0233、V0231、V0080、V0079 |
| Q0223 | mcq | V0231 | usage | V0231、V0232、V0233、V0236 |
| Q0224 | mcq | V0236 | usage | V0236、V0235、V0238、V0237、K0118 |
| Q0225 | mcq | V0237 | usage | V0237、V0234、V0236、V0235 |
| Q0229 | fill | G0056 | usage | G0056、V0188、V0177、V0244、K0108 |
| Q0232 | fill | G0060 | usage | G0060、V0170、V0121 |
| Q0233 | fill | G0062 | usage | G0062、V0254、V0252、V0128、K0124、K0125、K0120、K0121 |
| Q0234 | fill | G0063 | usage | G0063、V0245、V0085、V0131、K0109、K0110、K0075、K0076 |
| Q0238 | fill | G0067 | usage | G0067、G0031、V0249、V0040、K0106、K0116 |
| Q0242 | fill | G0057 | usage | G0057、G0031、V0082、V0081、K0071、K0072 |
| Q0243 | listen | V0244 | listening | V0244、V0188、V0247、G0073、V0234、V0090、K0108、K0112、K0113 |
| Q0244 | listen | V0259 | listening | V0259、V0258、V0189、V0177、V0184、V0193、K0131、K0130、K0080 |
| Q0246 | listen | V0187 | listening | V0187、V0092、V0169、V0186、V0248、K0119、K0114、K0115 |
| Q0247 | listen | V0097 | listening | V0097、V0096、V0118、V0192、V0133、V0030、K0082、K0083、K0084 |
| Q0249 | listen | V0250 | listening | V0250、V0251、V0191、V0169、K0118、K0119、G0046、K0117 |
| Q0250 | listen | V0253 | listening | V0253、V0254、V0252、V0088、V0240、G0073、K0122、K0123、K0124、K0125、K0120、K0121 |
| Q0251 | listen | V0198 | listening | V0198、V0220、V0095、V0176、V0123、G0034、K0081 |
| Q0252 | listen | V0244 | listening | V0244、V0247、V0248、V0236、V0208、G0065、V0161、K0108、K0112、K0113、K0114、K0115、K0136 |
| Q0253 | listen | V0186 | listening | V0186、V0091、V0096、V0185、V0196、V0206、G0065、K0084、K0090、K0135 |
| Q0254 | listen | V0260 | listening | V0260、V0213、V0252、V0246、V0170、V0176、G0085、K0132、K0120、K0121、K0089、K0111 |
| Q0255 | listen | V0221 | listening | V0221、V0222、V0224、V0202、V0116、V0125 |
| Q0256 | read | V0260 | reading | V0260、V0216、V0242、V0032、V0035、V0205、K0132、K0133、K0134 |
| Q0257 | read | V0244 | reading | V0244、V0247、V0242、V0185、V0090、V0169、V0205、K0108、K0112、K0113、K0133、K0134 |
| Q0258 | read | V0260 | reading | V0260、V0217、V0213、V0060、V0186、V0097、K0139、K0132、K0112、K0082、K0083 |
| Q0259 | read | V0198 | reading | V0198、V0220、V0223、V0218、V0100、V0136、V0205、K0140、K0087、K0088、K0133、K0134 |
| Q0260 | read | V0250 | reading | V0250、V0251、V0154、V0044、V0080、V0120、K0118、K0119、K0117、K0098、K0099 |
| Q0261 | read | V0187 | reading | V0187、V0186、V0185、V0242、V0169、V0116、V0248、K0114、K0115 |
| Q0262 | read | V0254 | reading | V0254、V0252、G0066、V0217、V0171、V0183、V0208、K0124、K0125、K0120、K0121、K0112、K0139、K0136 |
| Q0263 | read | V0187 | reading | V0187、V0242、V0042、V0169、V0161、V0085、V0026、K0104、K0075、K0076、K0096 |
| Q0264 | read | V0249 | reading | V0249、V0246、V0243、V0245、V0206、V0208、G0085、K0106、K0111、K0116、K0089、K0107、K0109、K0110、K0090、K0135、K0136 |
| Q0265 | read | V0219 | reading | V0219、V0220、V0205、V0206、V0227、V0228、G0085、K0083、K0133、K0134、K0090、K0135 |
| Q0266 | read | V0213 | reading | V0213、V0215、V0256、V0060、V0185、V0238、K0135、K0136、K0140、K0118 |
| Q0267 | read | G0079 | reading | G0079、G0069、G0058、V0159、V0172、V0179、V0081、V0153 |
| Q0268 | reorder | G0059 | usage | G0059、V0165、V0060、V0206、K0090、K0135 |
| Q0269 | reorder | G0074 | usage | G0074、V0209、V0081、V0082、K0071、K0072 |
| Q0270 | reorder | G0063 | usage | G0063、G0020、V0245、V0131、V0085、K0109、K0110、K0075、K0076 |
| Q0271 | reorder | G0056 | usage | G0056、V0188、V0244、V0144、K0108 |
| Q0272 | reorder | G0065 | usage | G0065、V0159、V0080、V0029 |
| Q0273 | reorder | G0073 | usage | G0073、V0170、V0231、V0008 |
| Q0274 | reorder | G0075 | usage | G0075、V0197、V0175、G0021 |
| Q0275 | reorder | G0077 | usage | G0077、G0035、V0210、V0179、V0081 |
| Q0276 | reorder | G0079 | usage | G0079、G0057、V0115、V0164、V0081 |
| Q0277 | reorder | G0085 | usage | G0085、V0246、V0245、V0125、V0085、K0089、K0111、K0109、K0110、K0075、K0076 |
| Q0278 | reorder | G0070 | usage | G0070、G0027、V0080、V0244、V0131、K0108 |
| Q0279 | reorder | G0058 | usage | G0058、G0026、V0234、V0244、V0115、K0108 |
| Q0280 | error_correct | V0259 | usage | V0259、V0258、V0189、V0043、K0131、K0079、K0080、K0130、K0077 |
| Q0281 | error_correct | V0232 | usage | V0232、V0233、V0231、V0079、V0080 |
| Q0282 | error_correct | V0234 | usage | V0234、V0237、V0079、V0038 |
| Q0283 | error_correct | G0052 | usage | G0052、V0151、V0076、V0083、K0073、K0074 |
| Q0284 | error_correct | G0025 | usage | G0025、G0038、V0239、V0115、V0124 |
| Q0285 | error_correct | G0055 | usage | G0055、V0250、V0215、V0242、K0135、K0117、K0140 |
| Q0286 | error_correct | G0084 | usage | G0084、V0242、V0186、V0060、V0122 |
| Q0287 | error_correct | G0084 | usage | G0084、V0253、V0212、V0108、K0122、K0123、K0137、K0138 |
| Q0288 | error_correct | G0019 | usage | G0019、G0059、G0021、V0244、V0108、K0108 |
| Q0289 | error_correct | V0181 | usage | V0181、V0182、V0156、G0052、K0072、K0128 |
| Q0290 | error_correct | G0060 | usage | G0060、V0170、V0150、V0079 |
| Q0291 | error_correct | V0236 | usage | V0236、V0238、G0036、V0244、V0123、K0118、K0108 |
| Q0292 | error_correct | G0025 | usage | G0025、G0038、V0126、V0088、V0106 |
| Q0293 | error_correct | G0047 | usage | G0047、G0046、V0244、V0103、V0165、K0108 |
| Q0298 | translate | V0232 | production | V0232、V0233、V0231、V0080、V0079 |
| Q0299 | translate | V0237 | production | V0237、V0234、V0040、V0186、V0169 |
| Q0320 | dialogue | V0234 | production | V0234、V0187、V0168、V0238、V0169、V0084、K0118 |
| Q0321 | dialogue | V0191 | production | V0191、V0239、V0182、V0007、V0221 |
| Q0331 | dialogue | V0200 | production | V0200、V0186、V0247、V0185、V0161、K0112、K0113 |
| Q0334 | mcq | V0262 | meaning | V0262 |
| Q0335 | mcq | V0263 | meaning | V0263 |
| Q0336 | mcq | V0264 | usage | V0264、G0026 |
| Q0338 | mcq | V0266 | usage | V0266、G0027 |
| Q0339 | mcq | V0270 | meaning | V0270 |
| Q0342 | mcq | V0298 | usage | V0298、V0299 |
| Q0343 | mcq | V0299 | meaning | V0299 |
| Q0355 | mcq | V0261 | usage | V0261、G0026、G0037、G0039 |
| Q0356 | mcq | V0261 | usage | V0261、V0272、V0277、V0244、V0185、G0065、G0026、G0019 |
| Q0357 | mcq | V0325 | usage | V0325、V0044、G0043、G0035、G0085、G0027 |
| Q0358 | mcq | V0286 | usage | V0286、V0282、V0291、V0251、V0273、V0292、G0026、G0019、G0039 |
| Q0359 | mcq | V0307 | usage | V0307、G0027、G0066、G0019 |
| Q0360 | mcq | V0321 | usage | V0321、V0310、V0041、G0055、G0024、G0026 |
| Q0361 | mcq | V0295 | usage | V0295、V0297、V0298、V0294、G0026、G0019、G0037 |
| Q0362 | mcq | V0261 | usage | V0261、V0277、G0073、G0026、G0019 |
| Q0363 | mcq | V0322 | usage | V0322、G0026、G0019、G0037 |
| Q0364 | mcq | V0266 | usage | V0266、V0272、V0261、G0051、G0032、G0026 |
| Q0365 | mcq | V0323 | usage | V0323、G0085、G0035、G0027 |
| Q0366 | mcq | V0284 | usage | V0284、V0273、V0292、V0250、G0026、G0024、G0019 |
| Q0367 | mcq | V0305 | usage | V0305、G0026、G0037、G0019 |
| Q0368 | mcq | V0315 | usage | V0315、V0044、V0043、G0035、G0027、G0019 |
| Q0369 | mcq | V0293 | usage | V0293、V0299、V0298、V0294、V0295、G0019、G0026、G0037 |
| Q0370 | mcq | V0262 | usage | V0262、V0272、G0073、G0051、G0019 |
| Q0371 | mcq | V0288 | usage | V0288、G0026、G0024、G0019 |
| Q0372 | mcq | V0280 | usage | V0280、V0267、V0289、V0217、G0065、G0026、G0019 |
| Q0373 | mcq | V0323 | usage | V0323、V0300、G0065、G0074、G0027 |
| Q0374 | mcq | V0287 | usage | V0287、V0281、V0273、V0314、G0026、G0035、G0019 |
| Q0375 | mcq | V0244 | usage | V0244、V0272、G0019、G0008 |
| Q0376 | mcq | V0244 | usage | V0244、V0272、G0019、G0008 |
| Q0377 | mcq | V0298 | usage | V0298、V0299、V0293、V0294、G0019、G0006 |
| Q0378 | mcq | V0298 | usage | V0298、V0299、V0293、V0294、G0019、G0006 |
| Q0379 | mcq | V0041 | usage | V0041、G0019、G0035 |
| Q0380 | mcq | V0041 | usage | V0041、G0019、G0035 |
| Q0381 | mcq | V0302 | usage | V0302、G0019、G0026 |
| Q0382 | mcq | V0270 | usage | V0270、G0073、G0019 |
| Q0383 | mcq | V0270 | usage | V0270、G0073、G0019 |
| Q0384 | mcq | V0296 | usage | V0296、G0019、G0025 |
| Q0385 | mcq | V0286 | usage | V0286、V0284、V0273、G0026、G0019 |
| Q0387 | mcq | V0272 | usage | V0272、G0019、G0026 |
| Q0388 | mcq | V0316 | usage | V0316、V0312、G0019、G0026 |
| Q0389 | mcq | V0303 | usage | V0303、G0019、G0026 |
| Q0390 | mcq | V0303 | usage | V0303、G0019、G0026 |
| Q0391 | mcq | V0299 | usage | V0299、V0294、G0019、G0035 |
| Q0392 | mcq | V0273 | usage | V0273、G0019、G0026 |
| Q0393 | mcq | V0313 | usage | V0313、G0019、G0026 |
| Q0394 | mcq | V0281 | usage | V0281、G0019、G0026 |
| Q0395 | mcq | V0279 | usage | V0279、G0019、G0026 |

## 全量明细

| 题目 | 类型 | 答案 | target | 能力 | context | 命中理由 |
|---|---|---|---|---|---|---|
| Q0001 | mcq | です | G0001 | usage | V0001、V0078、K0036、K0045、K0047 | R4 答案命中 pattern |
| Q0002 | fill | さん | V0003 | usage | G0001、V0079、K0048、K0047 | R2 答案等于词 surface |
| Q0003 | listen | です | G0001 | usage | V0001、V0078 | R4 答案命中 pattern |
| Q0004 | read | はい、学生です | G0001 | reading | V0078、V0001 | R7 无命中，回退 knowledge_ids[0]（fallback） |
| Q0005 | reorder | 2,3,1,4 | G0001 | usage | V0001、V0078 | R7 无命中，回退 knowledge_ids[0]（fallback） |
| Q0006 | error_correct | 私は学生です | G0001 | usage | V0001、V0078 | R1 答案与例句完全一致 |
| Q0007 | translate | — | G0001 | production | V0001、V0078 | R6 type=production → 首个语法 |
| Q0008 | free_production | — | G0001 | production | V0001、V0086 | R6 type=production → 首个语法 |
| Q0009 | dialogue | — | G0001 | production | V0001、V0004 | R6 type=production → 首个语法 |
| Q0010 | mcq | 何 | V0019 | usage | G0005、V0020 | R2 答案等于词 surface |
| Q0011 | fill | いくら | V0020 | usage | G0005、V0021 | R2 答案等于词 surface |
| Q0012 | listen | これは時計です | G0005 | listening | V0028、K0021 | R7 无命中，回退 knowledge_ids[0]（fallback） |
| Q0013 | read | 時計です | G0005 | reading | V0028、V0080、K0021 | R7 无命中，回退 knowledge_ids[0]（fallback） |
| Q0014 | reorder | 2,3,1,4 | G0005 | usage | V0019 | R7 无命中，回退 knowledge_ids[0]（fallback） |
| Q0015 | error_correct | これは本ですか | G0005 | usage | V0080 | R7 无命中，回退 knowledge_ids[0]（fallback） |
| Q0016 | translate | — | G0005 | production | V0019 | R6 type=production → 首个语法 |
| Q0017 | free_production | — | G0005 | production | V0020、V0021 | R6 type=production → 首个语法 |
| Q0018 | dialogue | — | G0005 | production | V0020、V0008 | R6 type=production → 首个语法 |
| Q0019 | mcq | でした | G0003 | usage | V0025、V0037、K0001、K0026 | R4 答案命中 pattern |
| Q0020 | fill | では | G0002 | usage | V0001、V0079、K0047、K0048 | R4 答案命中 pattern |
| Q0021 | listen | でした | G0003 | usage | V0025、V0037 | R4 答案命中 pattern |
| Q0022 | read | 火曜日です | G0003 | reading | G0001、V0031、V0032、V0023 | R7 无命中，回退 knowledge_ids[0]（fallback） |
| Q0023 | reorder | 2,3,1,4 | G0003 | usage | V0025、V0037 | R7 无命中，回退 knowledge_ids[0]（fallback） |
| Q0024 | error_correct | 私は先生ではありません | G0002 | usage | V0001、V0079 | R1 答案与例句完全一致 |
| Q0025 | translate | — | G0002 | production | V0001、V0079 | R6 type=production → 首个语法 |
| Q0026 | free_production | — | G0003 | production | V0025、V0036 | R6 type=production → 首个语法 |
| Q0027 | dialogue | — | G0002 | production | G0001、V0001、V0078、V0079 | R6 type=production → 首个语法 |
| Q0028 | mcq | も | G0004 | usage | V0001、V0078 | R4 答案命中 pattern |
| Q0029 | fill | の | G0006 | usage | V0001、V0080、K0057 | R4 答案命中 pattern |
| Q0030 | listen | も | G0004 | usage | V0001、V0078 | R4 答案命中 pattern |
| Q0031 | read | はい、学生です | G0004 | reading | V0001、V0078 | R7 无命中，回退 knowledge_ids[0]（fallback） |
| Q0032 | reorder | 2,3,1,4 | G0006 | usage | V0001、V0080 | R7 无命中，回退 knowledge_ids[0]（fallback） |
| Q0033 | error_correct | 私も学生です | G0004 | usage | V0001、V0078 | R1 答案与例句完全一致 |
| Q0034 | translate | — | G0004 | production | G0006、V0001、V0080 | R6 type=production → 首个语法 |
| Q0035 | free_production | — | G0004 | production | V0074、V0086 | R6 type=production → 首个语法 |
| Q0036 | dialogue | — | G0004 | production | V0006 | R6 type=production → 首个语法 |
| Q0037 | mcq | が | G0007 | usage | V0134、V0056 | R4 答案命中 pattern |
| Q0038 | fill | が | G0007 | usage | V0098、V0109 | R4 答案命中 pattern |
| Q0039 | listen | 猫がいます | G0007 | usage | V0098、V0109 | R1 答案与例句完全一致 |
| Q0040 | read | 魚です | G0007 | reading | V0134、V0056、V0055 | R7 无命中，回退 knowledge_ids[0]（fallback） |
| Q0041 | reorder | 2,3,1,4 | G0007 | usage | V0134、V0056 | R7 无命中，回退 knowledge_ids[0]（fallback） |
| Q0042 | error_correct | 猫がいます | G0007 | usage | G0014、V0098、V0109 | R1 答案与例句完全一致 |
| Q0043 | translate | — | G0007 | production | V0134、V0056、V0001 | R6 type=production → 首个语法 |
| Q0044 | free_production | — | G0007 | production | V0134、V0100、V0001 | R6 type=production → 首个语法 |
| Q0045 | dialogue | — | G0007 | production | V0134、V0054 | R6 type=production → 首个语法 |
| Q0046 | mcq | を | G0008 | usage | V0051、V0101、K0059 | R4 答案命中 pattern |
| Q0047 | fill | に | G0009 | usage | V0015、V0119 | R4 答案命中 pattern |
| Q0048 | listen | 水を飲みます | G0008 | listening | V0053、V0102、K0004、K0060 | R7 无命中，回退 knowledge_ids[0]（fallback） |
| Q0049 | read | 七時です | G0009 | reading | G0008、V0015、V0119、V0051 | R7 无命中，回退 knowledge_ids[0]（fallback） |
| Q0050 | reorder | 2,3,1,4 | G0008 | usage | V0051、V0101 | R7 无命中，回退 knowledge_ids[0]（fallback） |
| Q0051 | error_correct | 七時に起きます | G0009 | usage | V0015、V0119 | R1 答案与例句完全一致 |
| Q0052 | translate | — | G0008 | production | V0053、V0102、V0001 | R6 type=production → 首个语法 |
| Q0053 | free_production | — | G0008 | production | V0029、V0081、V0082 | R6 type=production → 首个语法 |
| Q0054 | dialogue | — | G0009 | production | G0008、V0015、V0119、V0052 | R6 type=production → 首个语法 |
| Q0055 | mcq | で | G0010 | usage | V0044、V0082、K0058 | R4 答案命中 pattern |
| Q0056 | fill | へ | G0011 | usage | V0024、V0039、V0103 | R4 答案命中 pattern |
| Q0057 | listen | 電車で行きます | G0010 | usage | V0060、V0103、K0053、K0054 | R1 答案与例句完全一致 |
| Q0058 | read | 図書館です | G0010 | reading | G0011、V0060、V0044、V0082 | R7 无命中，回退 knowledge_ids[0]（fallback） |
| Q0059 | reorder | 2,3,1,4 | G0011 | usage | V0039、V0103 | R7 无命中，回退 knowledge_ids[0]（fallback） |
| Q0060 | error_correct | 電車で行きます | G0010 | usage | V0060、V0103 | R1 答案与例句完全一致 |
| Q0061 | translate | — | G0010 | production | G0011、V0060、V0039、V0103、K0062 | R6 type=production → 首个语法 |
| Q0062 | free_production | — | G0010 | production | V0044、V0080、V0113 | R6 type=production → 首个语法 |
| Q0063 | dialogue | — | G0010 | production | G0011、V0063、V0103 | R6 type=production → 首个语法 |
| Q0064 | mcq | と | G0012 | usage | V0076、V0099、V0105 | R4 答案命中 pattern |
| Q0065 | fill | から | G0013 | usage | V0017、V0013、V0082 | R4 答案命中 pattern |
| Q0066 | listen | 友達と映画を見ます | G0012 | usage | V0076、V0099、V0105 | R1 答案与例句完全一致 |
| Q0067 | read | 友達です | G0012 | reading | G0013、V0076、V0041、V0039、V0036 | R7 无命中，回退 knowledge_ids[0]（fallback） |
| Q0068 | reorder | 2,4,3,1 | G0012 | usage | V0076、V0099、V0105 | R7 无命中，回退 knowledge_ids[0]（fallback） |
| Q0069 | error_correct | 九時から五時まで勉強します | G0013 | usage | V0017、V0013、V0082 | R1 答案与例句完全一致 |
| Q0070 | translate | — | G0012 | production | V0076、V0099、V0105 | R6 type=production → 首个语法 |
| Q0071 | free_production | — | G0013 | production | V0017、V0013、V0082 | R6 type=production → 首个语法 |
| Q0072 | dialogue | — | G0012 | production | V0072、V0099 | R6 type=production → 首个语法 |
| Q0073 | mcq | が | G0014 | usage | G0007、V0045、V0098、V0109 | R4 答案命中 pattern |
| Q0074 | fill | が | G0014 | usage | V0047、V0080、V0108 | R4 答案命中 pattern |
| Q0075 | listen | 駅の前に店があります | G0014 | usage | V0041、V0049、V0042、V0108、K0052、K0051、K0030 | R1 答案与例句完全一致 |
| Q0076 | read | 猫です | G0014 | reading | V0045、V0098、V0109 | R7 无命中，回退 knowledge_ids[0]（fallback） |
| Q0077 | reorder | 2,4,3,1 | G0014 | usage | V0045、V0098、V0109 | R7 无命中，回退 knowledge_ids[0]（fallback） |
| Q0078 | error_correct | 部屋に猫がいます | G0014 | usage | V0108、V0109、V0098、V0045 | R1 答案与例句完全一致 |
| Q0079 | translate | — | G0014 | production | V0045、V0098、V0109 | R6 type=production → 首个语法 |
| Q0080 | free_production | — | G0014 | production | V0044、V0080、V0108 | R6 type=production → 首个语法 |
| Q0081 | dialogue | — | G0014 | production | V0041、V0049、V0042、V0108 | R6 type=production → 首个语法 |
| Q0082 | mcq | 高い | V0125 | usage | G0015、V0080、K0057、K0068 | R2 答案等于词 surface |
| Q0083 | fill | 静か | V0136 | usage | G0016、V0045 | R2 答案等于词 surface |
| Q0084 | listen | この部屋は静かです | G0016 | usage | V0045、V0136 | R1 答案与例句完全一致 |
| Q0085 | read | はい、高いです | G0015 | reading | G0016、V0080、V0125、V0136 | R7 无命中，回退 knowledge_ids[0]（fallback） |
| Q0086 | reorder | 2,4,3,1 | G0015 | usage | V0080、V0125 | R7 无命中，回退 knowledge_ids[0]（fallback） |
| Q0087 | error_correct | 部屋は静かです | G0016 | usage | V0045、V0136 | R5 答案命中例句片段 |
| Q0088 | translate | — | G0016 | production | V0045、V0136 | R6 type=production → 首个语法 |
| Q0089 | free_production | — | G0016 | production | G0015、V0046、V0136、V0138 | R6 type=production → 首个语法 |
| Q0090 | dialogue | — | G0016 | production | G0015、V0136、V0128、V0140、V0148 | R6 type=production → 首个语法 |
| Q0091 | mcq | 高くない | G0017 | usage | V0125 | R5 答案命中例句片段 |
| Q0092 | fill | 寒かった | G0017 | usage | V0025、V0133 | R5 答案命中例句片段 |
| Q0093 | listen | 今日は寒くないです | G0017 | listening | V0133、V0023 | R7 无命中，回退 knowledge_ids[0]（fallback） |
| Q0094 | read | はい、寒かったです | G0017 | reading | V0025、V0133 | R7 无命中，回退 knowledge_ids[0]（fallback） |
| Q0095 | reorder | 2,4,3,1 | G0017 | usage | V0080、V0125 | R7 无命中，回退 knowledge_ids[0]（fallback） |
| Q0096 | error_correct | 昨日は寒かったです | G0017 | usage | V0025、V0133 | R1 答案与例句完全一致 |
| Q0097 | translate | — | G0017 | production | V0080、V0125 | R6 type=production → 首个语法 |
| Q0098 | free_production | — | G0017 | production | V0131、V0025、V0023 | R6 type=production → 首个语法 |
| Q0099 | dialogue | — | G0017 | production | V0132、V0081 | R6 type=production → 首个语法 |
| Q0100 | mcq | 食べます | G0019 | usage | V0101、K0059 | R5 答案命中例句片段 |
| Q0101 | fill | 行き | G0019 | usage | V0029、V0039、V0103、K0062 | R7 无命中，回退 knowledge_ids[0]（fallback） |
| Q0102 | listen | 本を読んでいます | G0020 | usage | G0027、V0080、V0113、K0057、K0065 | R1 答案与例句完全一致 |
| Q0103 | read | ご飯です | G0019 | reading | G0020、V0119、V0051、V0101 | R7 无命中，回退 knowledge_ids[0]（fallback） |
| Q0104 | reorder | 2,3,1,4 | G0020 | usage | G0019、V0051、V0101、V0103 | R7 无命中，回退 knowledge_ids[0]（fallback） |
| Q0105 | error_correct | 食べます | G0019 | usage | V0101 | R5 答案命中例句片段 |
| Q0106 | translate | — | G0020 | production | G0027、G0019、V0022、V0051、V0101 | R6 type=production → 首个语法 |
| Q0107 | free_production | — | G0020 | production | G0019、V0052、V0101、V0039、V0103 | R6 type=production → 首个语法 |
| Q0108 | dialogue | — | G0020 | production | G0027、V0080、V0113 | R6 type=production → 首个语法 |
| Q0109 | mcq | が | G0024 | usage | V0081、V0114、K0056、K0055 | R7 无命中，回退 knowledge_ids[0]（fallback） |
| Q0110 | fill | こと | G0039 | usage | V0081、V0114、V0111 | R4 答案命中 pattern |
| Q0111 | listen | 日本語が話せます | G0024 | usage | V0081、V0114 | R1 答案与例句完全一致 |
| Q0112 | read | いいえ、話せません | G0024 | reading | G0007、V0124、V0081、V0114 | R7 无命中，回退 knowledge_ids[0]（fallback） |
| Q0113 | reorder | 2,3,1,4 | G0024 | usage | V0081、V0114 | R7 无命中，回退 knowledge_ids[0]（fallback） |
| Q0114 | error_correct | 日本語が話せます | G0024 | usage | V0081、V0114 | R1 答案与例句完全一致 |
| Q0115 | translate | — | G0039 | production | V0081、V0114 | R6 type=production → 首个语法 |
| Q0116 | free_production | — | G0039 | production | V0081、V0114 | R6 type=production → 首个语法 |
| Q0117 | dialogue | — | G0024 | production | V0111、V0081、V0114、V0140 | R6 type=production → 首个语法 |
| Q0118 | mcq | と | G0036 | usage | V0024、V0096 | R4 答案命中 pattern |
| Q0119 | fill | なので | G0037 | usage | V0096、V0103 | R7 无命中，回退 knowledge_ids[0]（fallback） |
| Q0120 | listen | 明日は雨だと思います | G0036 | usage | V0024、V0096 | R1 答案与例句完全一致 |
| Q0121 | read | 雨が降っているからです | G0037 | reading | V0147、V0096、V0118、V0103 | R7 无命中，回退 knowledge_ids[0]（fallback） |
| Q0122 | reorder | 4,2,3,1 | G0036 | usage | V0024、V0096 | R7 无命中，回退 knowledge_ids[0]（fallback） |
| Q0123 | error_correct | 明日は雨だと思います | G0036 | usage | V0024、V0096 | R1 答案与例句完全一致 |
| Q0124 | translate | — | G0037 | production | V0131、V0103 | R6 type=production → 首个语法 |
| Q0125 | free_production | — | G0036 | production | V0024、V0097 | R6 type=production → 首个语法 |
| Q0126 | dialogue | — | G0036 | production | V0024、V0096 | R6 type=production → 首个语法 |
| Q0127 | mcq | に | G0050 | usage | V0079、V0078、V0080、V0113、K0057、K0065 | R7 无命中，回退 knowledge_ids[0]（fallback） |
| Q0128 | fill | に | G0049 | usage | V0096、V0118 | R7 无命中，回退 knowledge_ids[0]（fallback） |
| Q0129 | listen | 雨に降られました | G0049 | usage | V0096、V0118 | R1 答案与例句完全一致 |
| Q0130 | read | 雨です | G0049 | reading | V0096、V0118、V0038、V0122 | R7 无命中，回退 knowledge_ids[0]（fallback） |
| Q0131 | reorder | 2,4,3,1 | G0050 | usage | V0079、V0078、V0080、V0113 | R7 无命中，回退 knowledge_ids[0]（fallback） |
| Q0132 | error_correct | 先生は学生に本を読ませました | G0050 | usage | V0079、V0078、V0080、V0113 | R1 答案与例句完全一致 |
| Q0133 | translate | — | G0050 | production | V0079、V0078、V0080、V0113 | R6 type=production → 首个语法 |
| Q0134 | free_production | — | G0049 | production | V0096、V0118、V0025 | R6 type=production → 首个语法 |
| Q0135 | dialogue | — | G0049 | production | V0096、V0118 | R6 type=production → 首个语法 |
| Q0136 | mcq | に | G0052 | usage | V0076、V0081、V0121 | R7 无命中，回退 knowledge_ids[0]（fallback） |
| Q0137 | fill | あげました | G0052 | usage | V0001、V0076、V0081、V0121 | R5 答案命中例句片段 |
| Q0138 | listen | 友達に日本語を教えてもらいました | G0052 | usage | V0076、V0081、V0121 | R1 答案与例句完全一致 |
| Q0139 | read | 友達です | G0052 | reading | V0001、V0076、V0081、V0121、V0007 | R7 无命中，回退 knowledge_ids[0]（fallback） |
| Q0140 | reorder | 2,4,3,5,1 | G0052 | usage | V0001、V0076、V0081、V0121 | R7 无命中，回退 knowledge_ids[0]（fallback） |
| Q0141 | error_correct | 友達が私に教えてくれました | G0052 | usage | V0076、V0121 | R7 无命中，回退 knowledge_ids[0]（fallback） |
| Q0142 | translate | — | G0052 | production | V0076、V0081、V0121 | R6 type=production → 首个语法 |
| Q0143 | free_production | — | G0052 | production | V0001、V0076、V0081、V0121 | R6 type=production → 首个语法 |
| Q0144 | dialogue | — | G0052 | production | V0079、V0081、V0121、V0003 | R6 type=production → 首个语法 |
| Q0145 | mcq | 降り | G0043 | usage | V0096、V0118 | R7 无命中，回退 knowledge_ids[0]（fallback） |
| Q0146 | fill | かも | G0045 | usage | V0024、V0096 | R4 答案命中 pattern |
| Q0147 | listen | 明日は雨かもしれません | G0045 | usage | V0024、V0096 | R1 答案与例句完全一致 |
| Q0148 | read | 雨かもしれません | G0045 | usage | G0044、V0074、V0131、V0024、V0096 | R5 答案命中例句片段 |
| Q0149 | reorder | 2,3,1,4 | G0043 | usage | V0096、V0118 | R7 无命中，回退 knowledge_ids[0]（fallback） |
| Q0150 | error_correct | おいしそうです | G0043 | usage | V0130 | R7 无命中，回退 knowledge_ids[0]（fallback） |
| Q0151 | translate | — | G0043 | production | V0096、V0118 | R6 type=production → 首个语法 |
| Q0152 | free_production | — | G0045 | production | V0024、V0096 | R6 type=production → 首个语法 |
| Q0153 | dialogue | — | G0043 | production | V0096、V0118 | R6 type=production → 首个语法 |
| Q0154 | mcq | しなければ | G0046 | usage | V0083、V0107 | R5 答案命中例句片段 |
| Q0155 | fill | なくても | G0047 | usage | V0024、V0104 | R4 答案命中 pattern |
| Q0156 | listen | 宿題をしなければなりません | G0046 | usage | V0083、V0107 | R1 答案与例句完全一致 |
| Q0157 | read | しなければなりません | G0046 | usage | G0047、V0083、V0107、V0024 | R5 答案命中例句片段 |
| Q0158 | reorder | 2,3,1,4 | G0046 | usage | V0083、V0107 | R7 无命中，回退 knowledge_ids[0]（fallback） |
| Q0159 | error_correct | しなければなりません | G0046 | usage | V0083、V0107 | R5 答案命中例句片段 |
| Q0160 | translate | — | G0047 | production | V0024、V0104 | R6 type=production → 首个语法 |
| Q0161 | free_production | — | G0046 | production | V0029、V0081、V0082 | R6 type=production → 首个语法 |
| Q0162 | dialogue | — | G0046 | production | G0047、V0024、V0104 | R6 type=production → 首个语法 |
| Q0163 | mcq | せいで | G0054 | usage | V0096、V0103 | R4 答案命中 pattern |
| Q0164 | fill | はず | G0053 | usage | V0074、V0122、V0144 | R4 答案命中 pattern |
| Q0165 | listen | 先生のおかげで、日本語が上手になりました | G0054 | usage | V0079、V0081 | R1 答案与例句完全一致 |
| Q0166 | read | いいえ、美味しいわけではありません | G0053 | reading | V0125、V0130 | R7 无命中，回退 knowledge_ids[0]（fallback） |
| Q0167 | reorder | 2,4,3,1 | G0053 | usage | V0074、V0122 | R7 无命中，回退 knowledge_ids[0]（fallback） |
| Q0168 | error_correct | 雨のせいで、行けませんでした | G0054 | usage | V0096、V0103 | R1 答案与例句完全一致 |
| Q0169 | translate | — | G0054 | production | V0079、V0081 | R6 type=production → 首个语法 |
| Q0170 | free_production | — | G0053 | production | V0074、V0122、V0038 | R6 type=production → 首个语法 |
| Q0171 | dialogue | — | G0053 | production | V0125、V0130 | R6 type=production → 首个语法 |
| Q0172 | mcq | にとって | G0055 | usage | V0001、V0081、V0132、K0036、K0056 | R4 答案命中 pattern |
| Q0173 | fill | によって | G0055 | usage | V0077、K0032 | R4 答案命中 pattern |
| Q0174 | listen | 日本語について話します | G0055 | usage | V0081、V0114 | R1 答案与例句完全一致 |
| Q0175 | read | 日本語です | G0055 | reading | V0077、V0081、V0114 | R7 无命中，回退 knowledge_ids[0]（fallback） |
| Q0176 | reorder | 2,3,1,4 | G0055 | usage | V0001、V0081、V0132 | R7 无命中，回退 knowledge_ids[0]（fallback） |
| Q0177 | error_correct | 私にとって、日本語は難しいです | G0055 | usage | V0001、V0081、V0132 | R1 答案与例句完全一致 |
| Q0178 | translate | — | G0055 | production | V0001、V0081、V0132 | R6 type=production → 首个语法 |
| Q0179 | free_production | — | G0055 | production | V0081、V0114 | R6 type=production → 首个语法 |
| Q0180 | dialogue | — | G0055 | production | V0001、V0081、V0132、V0134 | R6 type=production → 首个语法 |
| Q0181 | mcq | は | G0001 | usage | V0001 | R4 答案命中 pattern |
| Q0182 | fill | です | G0001 | usage | V0001 | R4 答案命中 pattern |
| Q0183 | listen | おはようございます | V0006 | listening | — | R2 答案等于词 surface |
| Q0184 | mcq | 昼 | V0004 | usage | V0006、V0005 | R7 无命中，回退 knowledge_ids[0]（fallback） |
| Q0185 | error_correct | 私は李です | V0003 | usage | V0001、G0001 | R7 无命中，回退 knowledge_ids[0]（fallback） |
| Q0186 | translate | 晚上好 | V0005 | production | — | R6 type=production（无语法，取首项）（fallback） |
| Q0187 | free_production | — | G0001 | production | V0001 | R6 type=production → 首个语法 |
| Q0188 | dialogue | — | G0001 | production | V0004、V0001 | R6 type=production → 首个语法 |
| Q0189 | mcq | ではありません | G0002 | usage | — | R4 答案命中 pattern |
| Q0190 | fill | ございます | V0007 | usage | — | R7 无命中，回退 knowledge_ids[0]（fallback） |
| Q0191 | listen | すみません | V0008 | listening | — | R2 答案等于词 surface |
| Q0192 | mcq | さん | V0011 | reading | — | R2 答案等于词 kana |
| Q0193 | reorder | 1,2,3,4 | G0002 | usage | V0003 | R7 无命中，回退 knowledge_ids[0]（fallback） |
| Q0194 | error_correct | 私は先生ではありません | G0002 | usage | V0001 | R1 答案与例句完全一致 |
| Q0195 | mcq | でした | G0003 | usage | K0002 | R4 答案命中 pattern |
| Q0196 | fill | なな | V0015 | reading | — | R2 答案等于词 kana |
| Q0197 | listen | 九 | V0017 | listening | — | R2 答案等于词 surface |
| Q0198 | read | 金曜日 | K0006 | reading | K0007、V0023 | R7 无命中，回退 knowledge_ids[0]（fallback） |
| Q0199 | translate | 昨天是星期三 | G0003 | production | K0004、V0025 | R6 type=production → 首个语法 |
| Q0200 | error_correct | 私は学生でした | G0003 | usage | V0001 | R7 无命中，回退 knowledge_ids[0]（fallback） |
| Q0201 | mcq | も | G0004 | usage | V0021 | R4 答案命中 pattern |
| Q0202 | fill | いくら | V0020 | usage | — | R2 答案等于词 surface |
| Q0203 | listen | いくらですか | V0020 | listening | — | R7 无命中，回退 knowledge_ids[0]（fallback） |
| Q0204 | reorder | 1,2,3,4 | G0001 | usage | V0001 | R7 无命中，回退 knowledge_ids[0]（fallback） |
| Q0205 | mcq | えん | V0021 | reading | — | R2 答案等于词 kana |
| Q0206 | dialogue | — | V0020 | production | V0021、V0007 | R6 type=production（无语法，取首项）（fallback） |
| Q0207 | mcq | 明日 | V0024 | usage | V0025、V0023 | R2 答案等于词 surface |
| Q0208 | fill | きのう | V0025 | reading | — | R2 答案等于词 kana |
| Q0209 | listen | 明日 | V0024 | listening | V0026 | R2 答案等于词 surface |
| Q0210 | mcq | よん | V0012 | reading | K0011 | R2 答案等于词 kana |
| Q0211 | error_correct | 「毎日」は「まいにち」と読みます | V0029 | reading | K0001 | R7 无命中，回退 knowledge_ids[0]（fallback） |
| Q0212 | free_production | — | V0029 | production | V0026、V0027 | R6 type=production（无语法，取首项）（fallback） |
| Q0213 | mcq | かえって | V0198 | usage | V0220、V0095、V0102、K0081 | R2 答案等于词 surface |
| Q0214 | mcq | せっかく | V0197 | usage | V0196、V0059、V0101、V0130、K0089、K0090 | R2 答案等于词 surface |
| Q0215 | mcq | わざわざ | V0196 | usage | G0052、V0052、V0131、K0096、K0097 | R2 答案等于词 surface |
| Q0216 | mcq | 先生 | V0079 | usage | G0061、G0044、V0114 | R2 答案等于词 surface |
| Q0217 | mcq | そのため | V0204 | usage | V0096、V0207、G0037、K0084 | R2 答案等于词 surface |
| Q0218 | mcq | それとも | V0201 | usage | V0202、V0054、V0203、K0095 | R2 答案等于词 surface |
| Q0219 | mcq | ところで | V0200 | usage | V0244、V0188、V0171、V0186、K0108 | R2 答案等于词 surface |
| Q0220 | mcq | 見つかりました | V0241 | usage | V0240、V0154、V0155、G0007 | R7 无命中，回退 knowledge_ids[0]（fallback） |
| Q0221 | mcq | いらっしゃった | V0234 | usage | V0237、V0238、V0231、V0188、V0054、K0118、K0095 | R7 无命中，回退 knowledge_ids[0]（fallback） |
| Q0222 | mcq | ください | V0232 | usage | V0233、V0231、V0080、V0079 | R7 无命中，回退 knowledge_ids[0]（fallback） |
| Q0223 | mcq | いただいて | V0231 | usage | V0232、V0233、V0236 | R7 无命中，回退 knowledge_ids[0]（fallback） |
| Q0224 | mcq | おっしゃいました | V0236 | usage | V0235、V0238、V0237、K0118 | R7 无命中，回退 knowledge_ids[0]（fallback） |
| Q0225 | mcq | 伺い | V0237 | usage | V0234、V0236、V0235 | R7 无命中，回退 knowledge_ids[0]（fallback） |
| Q0226 | mcq | 遠慮 | V0239 | usage | V0221、V0177、V0225 | R2 答案等于词 surface |
| Q0227 | mcq | 看病 | V0259 | usage | V0258、V0189、V0043、K0131、K0079、K0080、K0130、K0077 | R2 答案等于词 surface |
| Q0228 | mcq | 記事 | V0260 | usage | G0056、V0207、V0256、K0132、K0076 | R2 答案等于词 surface |
| Q0229 | fill | 用意し | G0056 | usage | V0188、V0177、V0244、K0108 | R7 无命中，回退 knowledge_ids[0]（fallback） |
| Q0230 | fill | かどうか | G0058 | usage | V0244、V0234、V0124、K0108 | R4 答案命中 pattern |
| Q0231 | fill | 遅れた | G0059 | usage | V0165、V0175、V0060、V0206、K0090、K0135 | R5 答案命中例句片段 |
| Q0232 | fill | 説明し | G0060 | usage | V0170、V0121 | R7 无命中，回退 knowledge_ids[0]（fallback） |
| Q0233 | fill | 操作し | G0062 | usage | V0254、V0252、V0128、K0124、K0125、K0120、K0121 | R7 无命中，回退 knowledge_ids[0]（fallback） |
| Q0234 | fill | 残業し | G0063 | usage | V0245、V0085、V0131、K0109、K0110、K0075、K0076 | R7 无命中，回退 knowledge_ids[0]（fallback） |
| Q0235 | fill | 読む | V0113 | usage | G0064、V0260、V0081、V0209、K0132 | R2 答案等于词 surface |
| Q0236 | fill | 続ける | V0159 | usage | G0065、V0172、V0209 | R2 答案等于词 surface |
| Q0237 | fill | 忘れる | V0152 | usage | G0066、G0042、V0175、V0190 | R2 答案等于词 surface |
| Q0238 | fill | 就職しよう | G0067 | usage | G0031、V0249、V0040、K0106、K0116 | R7 无命中，回退 knowledge_ids[0]（fallback） |
| Q0239 | fill | 始める | V0160 | usage | G0069、V0244、V0116、K0108 | R2 答案等于词 surface |
| Q0240 | fill | 教えて | G0073 | usage | V0121、V0254、V0231、K0124、K0125 | R5 答案命中例句片段 |
| Q0241 | fill | ために | G0074 | usage | V0209、V0206、V0081、K0090、K0135 | R5 答案命中例句片段 |
| Q0242 | fill | いき | G0057 | usage | G0031、V0082、V0081、K0071、K0072 | R7 无命中，回退 knowledge_ids[0]（fallback） |
| Q0243 | listen | 部長と部下 | V0244 | listening | V0188、V0247、G0073、V0234、V0090、K0108、K0112、K0113 | R7 无命中，回退 knowledge_ids[0]（fallback） |
| Q0244 | listen | 母が入院していて、娘が看病している | V0259 | listening | V0258、V0189、V0177、V0184、V0193、K0131、K0130、K0080 | R7 无命中，回退 knowledge_ids[0]（fallback） |
| Q0245 | listen | 事故 | V0256 | listening | V0257、V0253、V0255、V0060、G0074、K0128、K0129、K0122、K0123、K0126、K0127 | R2 答案等于词 surface |
| Q0246 | listen | 駅が見える部屋 | V0187 | listening | V0092、V0169、V0186、V0248、K0119、K0114、K0115 | R7 无命中，回退 knowledge_ids[0]（fallback） |
| Q0247 | listen | 雨が降る | V0097 | listening | V0096、V0118、V0192、V0133、V0030、K0082、K0083、K0084 | R7 无命中，回退 knowledge_ids[0]（fallback） |
| Q0248 | listen | 不安 | V0223 | listening | V0249、G0053、V0185、V0171、V0195、V0221、K0106、K0116 | R2 答案等于词 surface |
| Q0249 | listen | 申請書に記入する | V0250 | listening | V0251、V0191、V0169、K0118、K0119、G0046、K0117 | R7 无命中，回退 knowledge_ids[0]（fallback） |
| Q0250 | listen | 故障して動かない | V0253 | listening | V0254、V0252、V0088、V0240、G0073、K0122、K0123、K0124、K0125、K0120、K0121 | R7 无命中，回退 knowledge_ids[0]（fallback） |
| Q0251 | listen | かえって気分が悪くなった | V0198 | listening | V0220、V0095、V0176、V0123、G0034、K0081 | R7 无命中，回退 knowledge_ids[0]（fallback） |
| Q0252 | listen | まだ決まっていない | V0244 | listening | V0247、V0248、V0236、V0208、G0065、V0161、K0108、K0112、K0113、K0114、K0115、K0136 | R7 无命中，回退 knowledge_ids[0]（fallback） |
| Q0253 | listen | ハイキングを延期する | V0186 | listening | V0091、V0096、V0185、V0196、V0206、G0065、K0084、K0090、K0135 | R7 无命中，回退 knowledge_ids[0]（fallback） |
| Q0254 | listen | メーカーが海外に工場を作ると発表した | V0260 | listening | V0213、V0252、V0246、V0170、V0176、G0085、K0132、K0120、K0121、K0089、K0111 | R7 无命中，回退 knowledge_ids[0]（fallback） |
| Q0255 | listen | 待たされて残念だった | V0221 | listening | V0222、V0224、V0202、V0116、V0125 | R7 无命中，回退 knowledge_ids[0]（fallback） |
| Q0256 | read | 出す曜日 | V0260 | reading | V0216、V0242、V0032、V0035、V0205、K0132、K0133、K0134 | R7 无命中，回退 knowledge_ids[0]（fallback） |
| Q0257 | read | 会議の開始時間が変わったこと | V0244 | reading | V0247、V0242、V0185、V0090、V0169、V0205、K0108、K0112、K0113、K0133、K0134 | R7 无命中，回退 knowledge_ids[0]（fallback） |
| Q0258 | read | 一部の列車が運休になる | V0260 | reading | V0217、V0213、V0060、V0186、V0097、K0139、K0132、K0112、K0082、K0083 | R7 无命中，回退 knowledge_ids[0]（fallback） |
| Q0259 | read | 寝る前に明るい画面を避け、体を休める準備をする | V0198 | reading | V0220、V0223、V0218、V0100、V0136、V0205、K0140、K0087、K0088、K0133、K0134 | R7 无命中，回退 knowledge_ids[0]（fallback） |
| Q0260 | read | 申請書への記入と身分証明になるもの | V0250 | reading | V0251、V0154、V0044、V0080、V0120、K0118、K0119、K0117、K0098、K0099 | R7 无命中，回退 knowledge_ids[0]（fallback） |
| Q0261 | read | 十八時を過ぎるなら連絡すること | V0187 | reading | V0186、V0185、V0242、V0169、V0116、V0248、K0114、K0115 | R7 无命中，回退 knowledge_ids[0]（fallback） |
| Q0262 | read | 通知が届かない・データが保存されない | V0254 | reading | V0252、G0066、V0217、V0171、V0183、V0208、K0124、K0125、K0120、K0121、K0112、K0139、K0136 | R7 无命中，回退 knowledge_ids[0]（fallback） |
| Q0263 | read | 開店時間 | V0187 | reading | V0242、V0042、V0169、V0161、V0085、V0026、K0104、K0075、K0076、K0096 | R7 无命中，回退 knowledge_ids[0]（fallback） |
| Q0264 | read | 就職で給料より働きやすさを重視する人が増加 | V0249 | reading | V0246、V0243、V0245、V0206、V0208、G0085、K0106、K0111、K0116、K0089、K0107、K0109、K0110、K0090、K0135、K0136 | R7 无命中，回退 knowledge_ids[0]（fallback） |
| Q0265 | read | 体調やその場の雰囲気による一時的な感じ | V0219 | reading | V0220、V0205、V0206、V0227、V0228、G0085、K0083、K0133、K0134、K0090、K0135 | R7 无命中，回退 knowledge_ids[0]（fallback） |
| Q0266 | read | 遅れの原因と状況を知らせ、代替を案内する | V0213 | reading | V0215、V0256、V0060、V0185、V0238、K0135、K0136、K0140、K0118 | R7 无命中，回退 knowledge_ids[0]（fallback） |
| Q0267 | read | 練習すればするほど上手になる | G0079 | reading | G0069、G0058、V0159、V0172、V0179、V0081、V0153 | R7 无命中，回退 knowledge_ids[0]（fallback） |
| Q0268 | reorder | 4,2,1,3 | G0059 | usage | V0165、V0060、V0206、K0090、K0135 | R7 无命中，回退 knowledge_ids[0]（fallback） |
| Q0269 | reorder | 4,2,1,3 | G0074 | usage | V0209、V0081、V0082、K0071、K0072 | R7 无命中，回退 knowledge_ids[0]（fallback） |
| Q0270 | reorder | 4,2,3,1 | G0063 | usage | G0020、V0245、V0131、V0085、K0109、K0110、K0075、K0076 | R7 无命中，回退 knowledge_ids[0]（fallback） |
| Q0271 | reorder | 4,1,2,3 | G0056 | usage | V0188、V0244、V0144、K0108 | R7 无命中，回退 knowledge_ids[0]（fallback） |
| Q0272 | reorder | 2,4,5,1,3 | G0065 | usage | V0159、V0080、V0029 | R7 无命中，回退 knowledge_ids[0]（fallback） |
| Q0273 | reorder | 4,2,3,1 | G0073 | usage | V0170、V0231、V0008 | R7 无命中，回退 knowledge_ids[0]（fallback） |
| Q0274 | reorder | 2,4,3,1 | G0075 | usage | V0197、V0175、G0021 | R7 无命中，回退 knowledge_ids[0]（fallback） |
| Q0275 | reorder | 4,2,1,3 | G0077 | usage | G0035、V0210、V0179、V0081 | R7 无命中，回退 knowledge_ids[0]（fallback） |
| Q0276 | reorder | 2,4,5,1,3 | G0079 | usage | G0057、V0115、V0164、V0081 | R7 无命中，回退 knowledge_ids[0]（fallback） |
| Q0277 | reorder | 4,5,2,1,3 | G0085 | usage | V0246、V0245、V0125、V0085、K0089、K0111、K0109、K0110、K0075、K0076 | R7 无命中，回退 knowledge_ids[0]（fallback） |
| Q0278 | reorder | 5,4,2,3,1 | G0070 | usage | G0027、V0080、V0244、V0131、K0108 | R7 无命中，回退 knowledge_ids[0]（fallback） |
| Q0279 | reorder | 4,2,1,3,5 | G0058 | usage | G0026、V0234、V0244、V0115、K0108 | R7 无命中，回退 knowledge_ids[0]（fallback） |
| Q0280 | error_correct | 熱があるので、今日は病院に診察を受けに行きます | V0259 | usage | V0258、V0189、V0043、K0131、K0079、K0080、K0130、K0077 | R7 无命中，回退 knowledge_ids[0]（fallback） |
| Q0281 | error_correct | 先生が私に辞書をくださいました | V0232 | usage | V0233、V0231、V0079、V0080 | R7 无命中，回退 knowledge_ids[0]（fallback） |
| Q0282 | error_correct | 明日、私は先生のお宅に伺います | V0234 | usage | V0237、V0079、V0038 | R7 无命中，回退 knowledge_ids[0]（fallback） |
| Q0283 | error_correct | 友達が私の宿題を手伝ってくれました | G0052 | usage | V0151、V0076、V0083、K0073、K0074 | R7 无命中，回退 knowledge_ids[0]（fallback） |
| Q0284 | error_correct | 分からないことがあったら、遠慮なく質問してください | G0025 | usage | G0038、V0239、V0115、V0124 | R7 无命中，回退 knowledge_ids[0]（fallback） |
| Q0285 | error_correct | この手続きは、窓口によって必要な書類が違います | G0055 | usage | V0250、V0215、V0242、K0135、K0117、K0140 | R7 无命中，回退 knowledge_ids[0]（fallback） |
| Q0286 | error_correct | 電車が止まったので、予定を変更せざるを得ませんでした | G0084 | usage | V0242、V0186、V0060、V0122 | R7 无命中，回退 knowledge_ids[0]（fallback） |
| Q0287 | error_correct | この機械でも、故障が起こり得ます | G0084 | usage | V0253、V0212、V0108、K0122、K0123、K0137、K0138 | R7 无命中，回退 knowledge_ids[0]（fallback） |
| Q0288 | error_correct | 昨日は会議がありました | G0019 | usage | G0059、G0021、V0244、V0108、K0108 | R7 无命中，回退 knowledge_ids[0]（fallback） |
| Q0289 | error_correct | 重い荷物を、丈夫な人に運んでもらいました | V0181 | usage | V0182、V0156、G0052、K0072、K0128 | R7 无命中，回退 knowledge_ids[0]（fallback） |
| Q0290 | error_correct | 私は先生に、もう一度ゆっくり説明してほしいです | G0060 | usage | V0170、V0150、V0079 | R7 无命中，回退 knowledge_ids[0]（fallback） |
| Q0291 | error_correct | 部長は明日は休むとおっしゃいました | V0236 | usage | V0238、G0036、V0244、V0123、K0118、K0108 | R7 无命中，回退 knowledge_ids[0]（fallback） |
| Q0292 | error_correct | 値段が安ければ、このパソコンを買います | G0025 | usage | G0038、V0126、V0088、V0106 | R7 无命中，回退 knowledge_ids[0]（fallback） |
| Q0293 | error_correct | 明日の会議は、行かなくてもいいです | G0047 | usage | G0046、V0244、V0103、V0165、K0108 | R7 无命中，回退 knowledge_ids[0]（fallback） |
| Q0294 | translate | — | G0054 | production | G0052、V0231、V0158、V0247、V0166、G0073、K0112、K0113 | R6 type=production → 首个语法 |
| Q0295 | translate | — | G0077 | production | G0057、V0164、V0243、V0223、V0193、G0048、K0106、K0107 | R6 type=production → 首个语法 |
| Q0296 | translate | — | G0052 | production | V0196、V0197、G0075、V0224、V0166、V0060 | R6 type=production → 首个语法 |
| Q0297 | translate | — | G0034 | production | V0199、V0198、V0245、V0242、V0206、G0036、K0109、K0110、K0090、K0135 | R6 type=production → 首个语法 |
| Q0298 | translate | — | V0232 | production | V0233、V0231、V0080、V0079 | R6 type=production（无语法，取首项）（fallback） |
| Q0299 | translate | — | V0237 | production | V0234、V0040、V0186、V0169 | R6 type=production（无语法，取首项）（fallback） |
| Q0300 | translate | — | G0055 | production | G0076、V0250、V0188、V0242、V0215、V0163、K0117、K0140 | R6 type=production → 首个语法 |
| Q0301 | translate | — | G0044 | production | G0043、V0234、V0235、V0248、V0122、V0030、K0114、K0115 | R6 type=production → 首个语法 |
| Q0302 | translate | — | G0079 | production | G0048、G0057、V0198、V0162、V0124、V0215、K0140 | R6 type=production → 首个语法 |
| Q0303 | translate | — | G0064 | production | G0065、G0074、V0165、V0141、V0027、V0103 | R6 type=production → 首个语法 |
| Q0304 | translate | — | G0076 | production | G0055、V0250、V0248、V0169、K0117、K0114、K0115 | R6 type=production → 首个语法 |
| Q0305 | translate | — | G0085 | production | G0058、V0246、V0245、V0242、V0226、G0037、K0089、K0111、K0109、K0110 | R6 type=production → 首个语法 |
| Q0306 | translate | — | G0073 | production | V0170、V0254、V0231、V0008、V0252、K0124、K0125、K0120、K0121 | R6 type=production → 首个语法 |
| Q0307 | free_production | — | G0085 | production | G0075、V0246、V0245、V0085、V0125、K0089、K0111、K0109、K0110、K0075、K0076 | R6 type=production → 首个语法 |
| Q0308 | free_production | — | G0068 | production | G0069、V0174、V0157、V0173、V0022 | R6 type=production → 首个语法 |
| Q0309 | free_production | — | G0071 | production | V0244、V0085、V0122、K0108、K0075、K0076 | R6 type=production → 首个语法 |
| Q0310 | free_production | — | G0070 | production | G0027、V0244、V0131、V0080、K0108 | R6 type=production → 首个语法 |
| Q0311 | free_production | — | G0072 | production | V0125、V0126、V0218、V0205、K0140、K0133、K0134 | R6 type=production → 首个语法 |
| Q0312 | free_production | — | G0083 | production | V0253、V0256、V0252、G0051、K0122、K0123、K0120、K0121 | R6 type=production → 首个语法 |
| Q0313 | free_production | — | G0084 | production | V0242、V0186、V0061、V0122 | R6 type=production → 首个语法 |
| Q0314 | free_production | — | G0082 | production | G0075、V0126、G0062、V0088 | R6 type=production → 首个语法 |
| Q0315 | free_production | — | G0080 | production | V0167、V0097、V0091、V0103、G0025、K0082、K0083 | R6 type=production → 首个语法 |
| Q0316 | free_production | — | G0078 | production | V0247、V0216、V0244、V0112、K0112、K0113、K0108 | R6 type=production → 首个语法 |
| Q0317 | free_production | — | G0081 | production | G0075、V0107、V0222、V0114、G0068 | R6 type=production → 首个语法 |
| Q0318 | free_production | — | G0066 | production | G0042、V0152、V0175、V0142、V0131 | R6 type=production → 首个语法 |
| Q0319 | free_production | — | G0060 | production | V0170、V0254、V0185、V0076、V0231、K0124、K0125 | R6 type=production → 首个语法 |
| Q0320 | dialogue | — | V0234 | production | V0187、V0168、V0238、V0169、V0084、K0118 | R6 type=production（无语法，取首项）（fallback） |
| Q0321 | dialogue | — | V0191 | production | V0239、V0182、V0007、V0221 | R6 type=production（无语法，取首项）（fallback） |
| Q0322 | dialogue | — | G0073 | production | V0170、V0231、V0008、V0244、K0108 | R6 type=production → 首个语法 |
| Q0323 | dialogue | — | G0059 | production | V0245、V0165、V0206、V0008、K0109、K0110、K0090、K0135 | R6 type=production → 首个语法 |
| Q0324 | dialogue | — | G0032 | production | V0190、G0065、V0051、V0042、K0097、K0104 | R6 type=production → 首个语法 |
| Q0325 | dialogue | — | G0075 | production | V0197、V0196、G0051、V0224、V0070 | R6 type=production → 首个语法 |
| Q0326 | dialogue | — | G0044 | production | G0043、V0234、V0122、V0156、K0128 | R6 type=production → 首个语法 |
| Q0327 | dialogue | — | G0058 | production | V0162、V0187、V0116、V0238、K0118 | R6 type=production → 首个语法 |
| Q0328 | dialogue | — | G0064 | production | V0170、V0254、V0244、V0169、K0124、K0125、K0108 | R6 type=production → 首个语法 |
| Q0329 | dialogue | — | G0071 | production | G0053、V0256、V0186、G0078 | R6 type=production → 首个语法 |
| Q0330 | dialogue | — | G0077 | production | G0057、V0210、V0164、V0194、V0081、V0140 | R6 type=production → 首个语法 |
| Q0331 | dialogue | — | V0200 | production | V0186、V0247、V0185、V0161、K0112、K0113 | R6 type=production（无语法，取首项）（fallback） |
| Q0332 | dialogue | — | G0051 | production | G0059、V0253、V0213、V0247、V0185、V0238、K0122、K0123、K0112、K0113、K0118 | R6 type=production → 首个语法 |
| Q0333 | mcq | かくにん | V0261 | reading | — | R2 答案等于词 kana |
| Q0334 | mcq | 研究讨论;探讨 | V0262 | meaning | — | R7 无命中，回退 knowledge_ids[0]（fallback） |
| Q0335 | mcq | 批准;认可 | V0263 | meaning | — | R7 无命中，回退 knowledge_ids[0]（fallback） |
| Q0336 | mcq | 提出して | V0264 | usage | G0026 | R7 无命中，回退 knowledge_ids[0]（fallback） |
| Q0337 | mcq | 締め切り | V0265 | usage | — | R2 答案等于词 surface |
| Q0338 | mcq | 担当して | V0266 | usage | G0027 | R7 无命中，回退 knowledge_ids[0]（fallback） |
| Q0339 | mcq | 交易对象;客户公司 | V0270 | meaning | — | R7 无命中，回退 knowledge_ids[0]（fallback） |
| Q0340 | mcq | 添付 | V0276 | usage | — | R2 答案等于词 surface |
| Q0341 | mcq | 運休 | V0310 | usage | V0309 | R2 答案等于词 surface |
| Q0342 | mcq | 押金,退租时扣除修缮费后可能退还 | V0298 | usage | V0299 | R7 无命中，回退 knowledge_ids[0]（fallback） |
| Q0343 | mcq | 公共区域费;物业公摊费 | V0299 | meaning | — | R7 无命中，回退 knowledge_ids[0]（fallback） |
| Q0344 | mcq | 症状 | V0301 | meaning | — | R2 答案等于词 surface |
| Q0345 | mcq | 処方 | V0303 | usage | — | R2 答案等于词 surface |
| Q0346 | mcq | 見込み | V0331 | usage | — | R2 答案等于词 surface |
| Q0347 | mcq | 傾向 | V0327 | usage | — | R2 答案等于词 surface |
| Q0348 | mcq | たびに | G0086 | usage | — | R4 答案命中 pattern |
| Q0349 | mcq | ついでに | G0087 | usage | — | R4 答案命中 pattern |
| Q0350 | mcq | うちに | G0088 | usage | — | R4 答案命中 pattern |
| Q0351 | mcq | 最中に | G0089 | usage | — | R4 答案命中 pattern |
| Q0352 | mcq | ばかりか | G0093 | usage | — | R4 答案命中 pattern |
| Q0353 | mcq | しよう | G0094 | usage | — | R5 答案命中例句片段 |
| Q0354 | mcq | はず | G0096 | usage | — | R4 答案命中 pattern |
| Q0355 | mcq | 次の平日に順延される | V0261 | usage | G0026、G0037、G0039 | R7 无命中，回退 knowledge_ids[0]（fallback） |
| Q0356 | mcq | 開催日と会議室 | V0261 | usage | V0272、V0277、V0244、V0185、G0065、G0026、G0019 | R7 无命中，回退 knowledge_ids[0]（fallback） |
| Q0357 | mcq | 去年より約一割増えた | V0325 | usage | V0044、G0043、G0035、G0085、G0027 | R7 无命中，回退 knowledge_ids[0]（fallback） |
| Q0358 | mcq | 本人が書いた委任状 | V0286 | usage | V0282、V0291、V0251、V0273、V0292、G0026、G0019、G0039 | R7 无命中，回退 knowledge_ids[0]（fallback） |
| Q0359 | mcq | 毎日ほぼ同じ時刻に寝て起きること | V0307 | usage | G0027、G0066、G0019 | R7 无命中，回退 knowledge_ids[0]（fallback） |
| Q0360 | mcq | 風が強ければ再開できないことがある | V0321 | usage | V0310、V0041、G0055、G0024、G0026 | R7 无命中，回退 knowledge_ids[0]（fallback） |
| Q0361 | mcq | 修理に使われ、残った分は返ってくる | V0295 | usage | V0297、V0298、V0294、G0026、G0019、G0037 | R7 无命中，回退 knowledge_ids[0]（fallback） |
| Q0362 | mcq | 午後から会場の準備があるから | V0261 | usage | V0277、G0073、G0026、G0019 | R7 无命中，回退 knowledge_ids[0]（fallback） |
| Q0363 | mcq | 車で来場する | V0322 | usage | G0026、G0019、G0037 | R7 无命中，回退 knowledge_ids[0]（fallback） |
| Q0364 | mcq | 毎月25日までに注文の確認をする | V0266 | usage | V0272、V0261、G0051、G0032、G0026 | R7 无命中，回退 knowledge_ids[0]（fallback） |
| Q0365 | mcq | 中心部の車の進入を制限し、無料バスを走らせる | V0323 | usage | G0085、G0035、G0027 | R7 无命中，回退 knowledge_ids[0]（fallback） |
| Q0366 | mcq | 文字が欠けている印鑑 | V0284 | usage | V0273、V0292、V0250、G0026、G0024、G0019 | R7 无命中，回退 knowledge_ids[0]（fallback） |
| Q0367 | mcq | すでに水分が足りなくなっている | V0305 | usage | G0026、G0037、G0019 | R7 无命中，回退 knowledge_ids[0]（fallback） |
| Q0368 | mcq | 20分 | V0315 | usage | V0044、V0043、G0035、G0027、G0019 | R7 无命中，回退 knowledge_ids[0]（fallback） |
| Q0369 | mcq | 建物の掃除とエレベーターの点検の費用 | V0293 | usage | V0299、V0298、V0294、V0295、G0019、G0026、G0037 | R7 无命中，回退 knowledge_ids[0]（fallback） |
| Q0370 | mcq | 来週の木曜日か金曜日 | V0262 | usage | V0272、G0073、G0051、G0019 | R7 无命中，回退 knowledge_ids[0]（fallback） |
| Q0371 | mcq | 許可証を車の前に貼っている車 | V0288 | usage | G0026、G0024、G0019 | R7 无命中，回退 knowledge_ids[0]（fallback） |
| Q0372 | mcq | 午後5時 | V0280 | usage | V0267、V0289、V0217、G0065、G0026、G0019 | R7 无命中，回退 knowledge_ids[0]（fallback） |
| Q0373 | mcq | 衛生管理の基準を満たすための設備 | V0323 | usage | V0300、G0065、G0074、G0027 | R7 无命中，回退 knowledge_ids[0]（fallback） |
| Q0374 | mcq | 新しい住所を届け出てから更新する | V0287 | usage | V0281、V0273、V0314、G0026、G0035、G0019 | R7 无命中，回退 knowledge_ids[0]（fallback） |
| Q0375 | mcq | 3時半 | V0244 | usage | V0272、G0019、G0008 | R7 无命中，回退 knowledge_ids[0]（fallback） |
| Q0376 | mcq | 15部 | V0244 | usage | V0272、G0019、G0008 | R7 无命中，回退 knowledge_ids[0]（fallback） |
| Q0377 | mcq | 家賃1か月分 | V0298 | usage | V0299、V0293、V0294、G0019、G0006 | R7 无命中，回退 knowledge_ids[0]（fallback） |
| Q0378 | mcq | 共益費に含まれず、別に払う | V0298 | usage | V0299、V0293、V0294、G0019、G0006 | R7 无命中，回退 knowledge_ids[0]（fallback） |
| Q0379 | mcq | 4番線 | V0041 | usage | G0019、G0035 | R7 无命中，回退 knowledge_ids[0]（fallback） |
| Q0380 | mcq | 10時15分 | V0041 | usage | G0019、G0035 | R7 无命中，回退 knowledge_ids[0]（fallback） |
| Q0381 | mcq | 10時半 | V0302 | usage | G0019、G0026 | R7 无命中，回退 knowledge_ids[0]（fallback） |
| Q0382 | mcq | 木曜日 | V0270 | usage | G0073、G0019 | R7 无命中，回退 knowledge_ids[0]（fallback） |
| Q0383 | mcq | 午前10時ごろ | V0270 | usage | G0073、G0019 | R7 无命中，回退 knowledge_ids[0]（fallback） |
| Q0384 | mcq | 土曜日の夕方6時ごろ | V0296 | usage | G0019、G0025 | R7 无命中，回退 knowledge_ids[0]（fallback） |
| Q0385 | mcq | 古い住所の住民票の写し | V0286 | usage | V0284、V0273、G0026、G0019 | R7 无命中，回退 knowledge_ids[0]（fallback） |
| Q0386 | mcq | 印鑑 | V0284 | usage | V0286、V0273、G0026、G0019 | R2 答案等于词 surface |
| Q0387 | mcq | 12部 | V0272 | usage | G0019、G0026 | R7 无命中，回退 knowledge_ids[0]（fallback） |
| Q0388 | mcq | 西門 | V0316 | usage | V0312、G0019、G0026 | R7 无命中，回退 knowledge_ids[0]（fallback） |
| Q0389 | mcq | 3回 | V0303 | usage | G0019、G0026 | R7 无命中，回退 knowledge_ids[0]（fallback） |
| Q0390 | mcq | 3日分 | V0303 | usage | G0019、G0026 | R7 无命中，回退 knowledge_ids[0]（fallback） |
| Q0391 | mcq | 6000円 | V0299 | usage | V0294、G0019、G0035 | R7 无命中，回退 knowledge_ids[0]（fallback） |
| Q0392 | mcq | 駅前の支社 | V0273 | usage | G0019、G0026 | R7 无命中，回退 knowledge_ids[0]（fallback） |
| Q0393 | mcq | 11時 | V0313 | usage | G0019、G0026 | R7 无命中，回退 knowledge_ids[0]（fallback） |
| Q0394 | mcq | 5日 | V0281 | usage | G0019、G0026 | R7 无命中，回退 knowledge_ids[0]（fallback） |
| Q0395 | mcq | 飛行機 | V0279 | usage | G0019、G0026 | R7 无命中，回退 knowledge_ids[0]（fallback） |
