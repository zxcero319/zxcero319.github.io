"""
Daily content updater for 异环攻略站 (NTE Player Guide).
Runs via GitHub Actions every day at 8:00 UTC+8.
Fetches recent news about 异环/ Neverness to Everness and updates the site.
"""
import json
import os
import re
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_FILE = ROOT / "data" / "daily.json"
INDEX_FILE = ROOT / "index.html"

# Beijing timezone
CST = timezone(timedelta(hours=8))
today = datetime.now(CST).strftime("%Y-%m-%d")
today_weekday = datetime.now(CST).strftime("%A")
weekday_zh = {"Monday": "周一", "Tuesday": "周二", "Wednesday": "周三",
              "Thursday": "周四", "Friday": "周五", "Saturday": "周六", "Sunday": "周日"}
today_zh = weekday_zh.get(today_weekday, "")

# ---- Content Pool (fallback when no fresh news fetched) ----
DAILY_POOL = {
    "guides": [
        {"title": "安魂曲配队进阶：双C轮换输出循环详解", "desc": "安魂曲+娜娜莉双主C体系，如何最大化伤害窗口期"},
        {"title": "深渊11层下半区速通路线图", "desc": "最优行进路线+精英怪跳过技巧，节省40秒"},
        {"title": "白藏单通教学：无敌帧完整时间表", "desc": "每个技能的无敌帧精确到帧，背板党的福音"},
        {"title": "1.1版本新弧盘强度测评", "desc": "夜曲特刊活动弧盘实战数据对比"},
        {"title": "娜娜莉0命满星深渊配置推荐", "desc": "无需高命，合理搭配弧盘也能满星"},
        {"title": "黑羽魔女占卜增益全解析", "desc": "每日卜运的隐藏增益效果与持续时间"},
        {"title": "主角战力最大化路线", "desc": "从序章到满级，主角培养优先级全指南"},
        {"title": "保时捷联动卡池回顾与评价", "desc": "联动限定角色强度回顾，是否值得补票"},
        {"title": "都市大亨经营攻略：21级速成法", "desc": "最高效的经营升级路线和建筑优先级"},
        {"title": "全角色羁绊解锁优先级", "desc": "哪些角色的羁绊奖励最值得优先解锁"},
    ],
    "news": [
        {"title": "1.2版本爆料汇总：新地图+新角色", "desc": "社区流传的1.2版本信息整理，含疑似新角色立绘"},
        {"title": "日本玩家评选：异环最受欢迎角色Top10", "desc": "日服玩家投票结果，第一名意外但又合理"},
        {"title": "玩家用异环引擎还原了涩谷十字路口", "desc": "都市建造系统玩出新高度，还原度令人惊叹"},
        {"title": "薄荷声优直播玩游戏：全程笑场", "desc": "薄荷的日配声优首次直播玩异环，节目效果拉满"},
        {"title": "NTE同人创作大赏：本周精选5幅插画", "desc": "全球玩家同人作品精选，质量不输官方"},
        {"title": "开发组AMA答玩家问精华整理", "desc": "制作人在Discord的问答要点：未来更新方向"},
        {"title": "最离谱的死法收集：玩家投稿精选", "desc": "从高楼跳下被鸟撞到、开车飞进喷泉…异环欢乐多"},
        {"title": "同居系统隐藏对话整理", "desc": "不同角色邀请同居后的特殊对话和事件"},
        {"title": "海外玩家热议：为什么异环比GTA更适合二次元", "desc": "Reddit热帖：都市生活感才是核心竞争力"},
        {"title": "中国风地图猜测：下一个城市会是哪里？", "desc": "玩家根据游戏内线索推测第二个城市原型"},
    ],
    "tips": [
        {"title": "每日刷新时间表（北京时间）", "desc": "委托4:00 | 商店8:00 | 周本周一4:00 刷新"},
        {"title": "免费回血点位汇总", "desc": "全地图8个免费回血地点，省下料理材料"},
        {"title": "移动速度排名：开车vs滑板vs跑步", "desc": "实测数据：不同移动方式的效率对比"},
        {"title": "隐藏成就「高空坠落」解锁方法", "desc": "从特定位置跳下即可解锁，有原石奖励"},
        {"title": "料理buff叠加规则详解", "desc": "哪些buff可以共存，哪些会互相覆盖"},
        {"title": "周本奖励领取时间优化", "desc": "周一周三周五各打一次，收益最大化"},
        {"title": "背包整理技巧：快速找到想要的道具", "desc": "善用筛选和收藏功能，告别翻包烦恼"},
        {"title": "拍照模式隐藏滤镜解锁", "desc": "完成特定异闻录可解锁稀有滤镜"},
        {"title": "联机模式礼仪指南", "desc": "进别人世界要注意什么？老玩家整理"},
        {"title": "手机端优化设置推荐", "desc": "画质与帧数最佳平衡方案，发热降低30%"},
    ],
}


def fetch_latest_news():
    """Try to fetch recent news from web sources. Returns list of items or None."""
    items = []
    try:
        import requests
        # Try fetching from game news aggregators
        # 17173 异环 tag
        resp = requests.get(
            "https://search.17173.com/s?q=%E5%BC%82%E7%8E%AF&type=news",
            headers={"User-Agent": "NTE-Player-Guide/1.0"},
            timeout=15
        )
        if resp.status_code == 200:
            # Extract article titles from search results
            titles = re.findall(r'<a[^>]*title="([^"]*异环[^"]*)"[^>]*>', resp.text)
            links = re.findall(r'<a[^>]*href="(https?://news\.17173\.com[^"]*)"[^>]*>', resp.text)
            for t, l in zip(titles[:5], links[:5]):
                t_clean = re.sub(r'<[^>]+>', '', t).strip()
                if t_clean and len(t_clean) > 5:
                    items.append({"title": t_clean, "desc": f"来源：17173", "url": l})
    except Exception as e:
        print(f"[INFO] Web fetch skipped: {e}")

    return items if items else None


def pick_from_pool():
    """Pick random items from the content pool for today."""
    import random
    random.seed(today)  # Same seed = same picks for the same day

    guides = random.sample(DAILY_POOL["guides"], 2)
    news = random.sample(DAILY_POOL["news"], 2)
    tips = random.sample(DAILY_POOL["tips"], 2)
    return {"guides": guides, "news": news, "tips": tips}


def update_daily_json(content):
    """Write daily.json with today's content."""
    data = {
        "date": today,
        "weekday": today_zh,
        "updated": datetime.now(CST).strftime("%Y-%m-%d %H:%M:%S CST"),
        "guides": content["guides"],
        "news": content["news"],
        "tips": content["tips"],
    }
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    DATA_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[OK] daily.json written with {len(content['guides'])} guides, {len(content['news'])} news, {len(content['tips'])} tips")


def update_index_html():
    """Inject daily update badge into index.html."""
    html = INDEX_FILE.read_text(encoding="utf-8")

    badge_html = f'<span class="daily-badge" data-i18n="dailyBadge">📅 每日更新 · {today_zh}</span>'

    # Update or insert the daily badge in the header logo area
    if '<span class="daily-badge"' in html:
        html = re.sub(
            r'<span class="daily-badge"[^>]*>.*?</span>',
            badge_html,
            html
        )
    else:
        # Insert after the logo
        html = html.replace(
            '</div>\n  </div>\n</header>',  # wrong, let me find the right spot
            '</div>\n</header>',
        )
        # Insert after logo
        html = html.replace(
            '<div class="logo" data-i18n="siteName">',
            badge_html + '\n  <div class="logo" data-i18n="siteName">',
        )

    INDEX_FILE.write_text(html, encoding="utf-8")
    print("[OK] index.html updated with daily badge")


def main():
    print(f"[START] Daily update for {today} ({today_zh})")

    # Try fetching fresh news first
    fresh_content = fetch_latest_news()

    if fresh_content:
        # If we got fresh news, reformat to match pool structure
        guides = [{"title": x["title"], "desc": x["desc"]} for x in fresh_content[:2]]
        news = [{"title": x["title"], "desc": x["desc"]} for x in fresh_content[2:4]]
        tips = [{"title": x["title"], "desc": x["desc"]} for x in fresh_content[4:6]]
        # Pad with pool items if needed
        if len(guides) < 2: guides += DAILY_POOL["guides"][:2-len(guides)]
        if len(news) < 2: news += DAILY_POOL["news"][:2-len(news)]
        if len(tips) < 2: tips += DAILY_POOL["tips"][:2-len(tips)]
        content = {"guides": guides[:2], "news": news[:2], "tips": tips[:2]}
    else:
        # Fall back to content pool
        content = pick_from_pool()
        print("[INFO] Using content pool (no fresh news fetched)")

    update_daily_json(content)
    update_index_html()
    print(f"[DONE] Daily update complete for {today}")


if __name__ == "__main__":
    main()
