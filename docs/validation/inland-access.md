# Inland-access checkpoint validation

Implementation: `4331981` on `t3/inland-access`. Subsequent evidence-only commits do not change the tested implementation. Native replay uses `SLOPPY_THREADS=1`, `SLOPPY_NO_AUDIO=1`, empty display variables and a private save directory. One seed runs at a time.

The original combined `tests/living_market.jo` run ended with SIGTERM before a result. These individual executions run its unchanged 43,200-minute loop and hourly money, goods, inventory and price assertions, with daily progress logging. They do not claim the separate fisher/cancelled-shipment test or `living_save` suite passed.

Replay artifacts: `/var/home/david/dev/tmp/aegean-skies/towns/inland/market-seed{,.jo}`; logs `market-seed-<seed>.log`. Invoke `market-seed <seed>` with the environment above.

| File | SHA-256 |
| --- | --- |
| Original test | `54340c13b80d90890b4a6de54514b401234d3ac19a8ee1d7dc3f91aeef19ab65` |
| Individual-seed source | `bb63d77016b10b5ae7723713a72ba10982f159cd18316d9ef78567d276afd8bb` |
| Release replay binary | `48632851aab60d3d99c6e1fc2c8899c10cdd14a7df9b60566b5f9edbd8727e20` |

| Seed | Result | Final accounting | Log SHA-256 |
| --- | --- | --- | --- |
| 0 | PASS, 30 days | 3311926c in, 1079835c out, balanced | `dbe742d6c015f859c1dbed876cba54566aa49cc2c5b0b5df0a043065ca695e29` |
| 1 | PASS, 30 days | 3234889c in, 1099872c out, balanced | `0aa9a51c3eea62b43aed5a06de263253dd8c6ae3b74a798532c8761d0c7cb268` |
| 7 | PASS, 30 days | 3305902c in, 1092342c out, balanced | `abac92151e1e0ae37c52460a1106c98d4d470ab34d852ac4d34f6b0ca50b2238` |
| 42 | PASS, 30 days | 3373695c in, 1058070c out, balanced | `c2c88b7706ae6e2a53f2aa7fc7df4e12b7e4137447b062bea9ce37dbfbcac8a7` |
| 127 | PASS, 30 days | 3343364c in, 1084848c out, balanced | `a8e0d16adf0c9e29040fd4236b2de46f5871b0fe83de8f5fca92cc0c959975a1` |

All five 30-day market seeds pass. Pending: the classified island-access hand-off. No Redfox run is part of this resume.
