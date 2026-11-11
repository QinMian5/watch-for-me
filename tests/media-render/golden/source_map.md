# Checkout payment retries — design review
来源：recordings/checkout-design-review.mp4 ｜ video ｜ 00:07:10 ｜ en→zh-CN ｜ dialogic ｜ whisper-asr
说话人：
- Dana Lee = SPK001
- Priya Nair = SPK002
- 说话人 1 = SPK003
局限：
- 00:04:49–00:05:40 coverage：录音中断约 51 秒，这段内容缺失。
- 00:01:57–00:02:09 speaker：S006 与上一句重叠，归属为 Dana Lee 的把握较低。
（由 source_map.json 确定性生成，勿手改；sha256 b5e481036391）

[00:00:05–00:00:21] Dana Lee (S001)
  Thanks for joining. The goal today is to decide how checkout handles payment retries, because last month's incident double-charged about two hundred customers.
[00:00:22–00:01:14] Priya Nair (S002–S003)
  The root cause is that the client retries on a timeout, but the server may have already captured the payment. We have no idempotency key, so the second attempt looks like a new charge. My proposal is a server-generated idempotency key stored for twenty-four hours. If the same key arrives again, we return the first result.
[00:01:16–00:01:38] 说话人 1 (S004)
  I worry about the twenty-four hour window. Bank transfers can settle after two days, so a retry on day three would still double-charge.
[00:01:39–00:01:58] Priya Nair (S005)
  Transfers don't go through this path today, so I'd keep it at twenty-four hours for cards and revisit when we add transfers.
[00:01:57–00:02:09] Dana Lee? (S006)
  Right, and storage cost is not really the constraint here, is it?
[00:02:10–00:02:31] 说话人 1 (S007) 低置信:S007
  It's cheap. Uh, maybe forty... forty gigs a month at current volume.
[00:02:40–00:04:48] Priya Nair (S008–S012)
  Let me show how I'd roll it out. First, turn on the flag in shadow mode, so keys are written but never enforced. The command is rollout set idempotency, mode shadow, percent five. We start at five percent so a bug in key generation can't touch most traffic. Now watch the dashboard. The panel you want is would-have-deduped. It should stay near zero except for real client retries. If that panel jumps above one percent, roll back by setting the mode to off. That's a sign keys are colliding. Once it's flat for a full day, switch to enforce at five percent, then go to a hundred. Ramping through twenty-five is optional, I'd only do it before a holiday.
[00:05:41–00:06:02] Dana Lee (S013)
  Okay. Let's go with the server-side key and twenty-four hours for cards. That's decided.
[00:06:03–00:06:20] 说话人 1 (S014)
  I still think the window should be configurable per payment method. I don't want to be hard-coding this again.
[00:06:21–00:06:33] Dana Lee (S015)
  Let's keep that as an open question until transfers are on the roadmap.
[00:06:34–00:06:52] Priya Nair (S016)
  I'll have the shadow rollout up by Friday.
[00:06:53–00:07:08] 说话人 1 (S017)
  Someone should probably update the client retry docs.
[00:07:09–00:07:10] 说话人未辨 (S018) 低置信:S018
  (crosstalk) ...and the changelog too.
