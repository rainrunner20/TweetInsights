"""Self-contained HTML dashboard. Never loads scripts, styles, or data externally."""

from html import escape


def render_dashboard(result: dict, *, sample_data: bool = False) -> str:
    current = result["current"]
    previous = result["previous"]
    trends = result["top_hashtags"]
    max_mentions = max((t["mentions"] for t in trends), default=1)

    def stat(label: str, value: int, old: int) -> str:
        difference = value - old
        sign = "+" if difference > 0 else ""
        return (
            '<div class="stat"><div class="kicker">' + escape(label) + '</div>'
            + f'<div class="number">{value:,}</div>'
            + f'<div class="hint">{sign}{difference:,} vs previous window</div></div>'
        )

    bars = "".join(
        '<div class="trend">'
        f'<div class="tag">#{escape(t["hashtag"])}</div>'
        '<div class="track"><div class="bar" style="width:'
        f'{100 * t["mentions"] / max_mentions:.2f}%"></div></div>'
        f'<div class="count">{t["mentions"]} posts</div>'
        f'<div class="delta">{t["change"]:+d}</div></div>'
        for t in trends
    ) or '<p class="empty">No hashtags were recorded in this window.</p>'
    dataset_label = "SYNTHETIC SAMPLE DATA" if sample_data else "USER-PROVIDED CSV"
    start = escape(result["window"]["start"][:10])
    end = escape(result["window"]["end"][:10])
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>TweetInsights | Topic Pulse</title>
<style>
:root {{ color-scheme:dark; font-family:Inter, ui-sans-serif, system-ui, -apple-system, Segoe UI, sans-serif; background:#0c1018; color:#ebeff5; }}
* {{box-sizing:border-box}} body {{margin:0; min-height:100vh; background:radial-gradient(ellipse at 90% 0%,#17333e 0%,transparent 40%),#0c1018;}}
main {{max-width:1100px;margin:0 auto;padding:60px 28px 90px}} .label {{color:#78f4ce;letter-spacing:.15em;font-weight:750;font-size:12px}}
h1 {{font-size:clamp(42px,7vw,82px);letter-spacing:-.065em;margin:12px 0 6px;line-height:1}} .sub {{color:#a9b6c5;max-width:680px;line-height:1.6}}
.pill {{display:inline-block;border:1px solid #3b6873;border-radius:99px;padding:7px 11px;font-size:12px;font-weight:700;color:#b6eade;margin:18px 0}}
.metrics {{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:16px;margin-top:36px}} .stat,.panel {{border:1px solid #27313e;background:#141d29d9;border-radius:17px;padding:24px}}
.kicker {{color:#a4b8c6;text-transform:uppercase;letter-spacing:.1em;font-size:12px;font-weight:750}} .number {{font-size:46px;font-weight:800;letter-spacing:-.06em;margin:12px 0}} .hint {{color:#80eac9;font-size:13px}}
.panel {{margin-top:18px;padding:28px}} h2 {{margin:0 0 6px;font-size:24px;letter-spacing:-.03em}} .desc {{color:#9eafbd;font-size:14px;margin-bottom:26px;line-height:1.6}}
.trend {{display:grid;grid-template-columns:160px 1fr 80px 52px;gap:14px;align-items:center;margin:18px 0}} .tag {{font-weight:700;overflow-wrap:anywhere}}
.track {{border-radius:8px;background:#263343;height:15px;overflow:hidden}} .bar {{height:100%;border-radius:8px;background:linear-gradient(90deg,#55d9dc,#a1fac9)}}
.count {{font-size:13px;color:#b7c5cf;text-align:right}} .delta {{font-size:13px;text-align:right;color:#95ffce}}
footer {{margin-top:22px;font-size:12px;line-height:1.7;color:#8d9aa7}} .empty {{color:#a7b8c7}}
@media(max-width:700px) {{main {{padding:38px 16px}} .metrics {{grid-template-columns:1fr}} .trend {{grid-template-columns:100px 1fr 55px;gap:8px}} .delta {{display:none}} .panel {{padding:18px}}}}
</style></head><body><main>
<div class="label">TWEETINSIGHTS / ANALYTICS</div><h1>Topic Pulse<span style="color:#7bf0d1">.</span></h1>
<p class="sub">A reproducible look at which conversations are gaining momentum. Current window: {start} to {end} (end exclusive, UTC).</p>
<div class="pill">{dataset_label}</div>
<section class="metrics" aria-label="Window metrics">
{stat("Posts", current["posts"], previous["posts"])}
{stat("Likes", current["likes"], previous["likes"])}
{stat("Reposts", current["reposts"], previous["reposts"])}
</section><section class="panel"><h2>Emerging hashtags</h2>
<p class="desc">Each topic is counted once per post. Rank uses change in mentions weighted by current volume. Values are descriptive, not predictions.</p>
{bars}</section>
<footer>Offline report · {result["source_posts"]:,} source posts · {escape(result["method"])}<br>
Only posts inside the two comparison windows affect the totals. No live X/Twitter API, sentiment classifier, or streaming system is connected.</footer>
</main></body></html>'''
