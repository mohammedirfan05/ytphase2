import csv
import json
import statistics
import sys

sys.stdout.reconfigure(encoding='utf-8')

csv_path = r"data/Content 2026-07-16_2026-08-13 Dont Mix This/Content_Table data.csv"

with open(csv_path, mode="r", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    rows = [r for r in reader if r["Content"] != "Total" and r["Content"].strip() != ""]

data = []
for r in rows:
    try:
        views = int(r["Views"]) if r["Views"] else 0
        engaged_views = int(r["Engaged views"]) if r["Engaged views"] else 0
        apv = float(r["Average percentage viewed (%)"]) if r["Average percentage viewed (%)"] else 0.0
        stayed = float(r["Stayed to watch (%)"]) if r["Stayed to watch (%)"] else 0.0
        dur = int(r["Duration"]) if r["Duration"] else 0
        subs_gained = int(r["Subscribers gained"]) if r["Subscribers gained"] else 0
        subs_net = int(r["Subscribers"]) if r["Subscribers"] else 0
        likes = int(r["Likes"]) if r["Likes"] else 0
        comments = int(r["Comments added"]) if r["Comments added"] else 0
        shares = int(r["Shares"]) if r["Shares"] else 0
        ctr = float(r["Impressions click-through rate (%)"]) if r["Impressions click-through rate (%)"] else 0.0
        title = r["Video title"]
        pub = r["Video publish time"]
        video_id = r["Content"]
        
        # Categorize topic
        t_lower = title.lower()
        if any(w in t_lower for w in ["marvel", "dc", "hulk", "batman", "iron man", "thor", "odin", "wolverine", "deadpool", "darkhold", "superman", "shazam", "venom", "carnage", "vision", "loki", "doctor doom", "wanda", "strange", "gauntlet", "homelander", "war machine", "mjolnir", "adamantium", "spiderverse", "hela", "thanos"]):
            category = "Marvel/DC Superhero"
        elif any(w in t_lower for w in ["jjk", "jujutsu", "sharingan", "naruto", "anime"]):
            category = "Anime"
        elif any(w in t_lower for w in ["dragon", "dracula", "vampire", "god", "zeus", "poseidon", "mythology"]):
            category = "Mythology/Creatures"
        else:
            category = "General Knowledge / Off-Cluster"
            
        # Hook classification (approximate based on title / structure)
        if any(w in t_lower for w in ["terms you've been mixing", "you still don't know", "99% of marvel", "you've been wrong"]):
            hook_type = "Audience Challenge / Myth"
        elif any(w in t_lower for w in ["why ", "which ", "who is", "is doctor doom", "what makes"]):
            hook_type = "Question / Curiosity Anchor"
        elif any(w in t_lower for w in [" vs ", "v/s", ": "]) and not "why" in t_lower:
            hook_type = "Direct Contrast / Entity Comparison"
        elif any(w in t_lower for w in ["is not", "not even close"]):
            hook_type = "Contrarian / Negation"
        else:
            hook_type = "Direct / Other"
        
        # Composite retention/stickiness score (normalized APV & Stayed to watch)
        composite_score = (apv * 0.6) + (stayed * 0.4)
        
        data.append({
            "id": video_id,
            "title": title,
            "pub": pub,
            "duration": dur,
            "views": views,
            "engaged_views": engaged_views,
            "apv": apv,
            "stayed": stayed,
            "subs_gained": subs_gained,
            "subs_net": subs_net,
            "likes": likes,
            "comments": comments,
            "shares": shares,
            "ctr": ctr,
            "composite_score": composite_score,
            "category": category,
            "hook_type": hook_type
        })
    except Exception as e:
        print(f"Error parsing row: {e}")

print(f"Total videos analyzed: {len(data)}")

# Sort by APV
by_apv = sorted(data, key=lambda x: x["apv"], reverse=True)
print("\n========================================================")
print("TOP 10 BY APV (RETENTION %)")
print("========================================================")
for i, v in enumerate(by_apv[:10], 1):
    print(f"{i:2d}. {v['title'][:42]:<42} | APV: {v['apv']:5.1f}% | Stayed: {v['stayed']:5.1f}% | Views: {v['views']:5d} | Dur: {v['duration']}s | Subs: {v['subs_gained']} | Cat: {v['category']}")

print("\n========================================================")
print("BOTTOM 10 BY APV (RETENTION %)")
print("========================================================")
for i, v in enumerate(by_apv[-10:], 1):
    print(f"{i:2d}. {v['title'][:42]:<42} | APV: {v['apv']:5.1f}% | Stayed: {v['stayed']:5.1f}% | Views: {v['views']:5d} | Dur: {v['duration']}s | Subs: {v['subs_gained']} | Cat: {v['category']}")

# Sort by Stayed to watch %
by_stayed = sorted(data, key=lambda x: x["stayed"], reverse=True)
print("\n========================================================")
print("TOP 10 BY STAYED-TO-WATCH % (SWIPE-THROUGH RESISTANCE)")
print("========================================================")
for i, v in enumerate(by_stayed[:10], 1):
    print(f"{i:2d}. {v['title'][:42]:<42} | Stayed: {v['stayed']:5.1f}% | APV: {v['apv']:5.1f}% | Views: {v['views']:5d} | Dur: {v['duration']}s")

print("\n========================================================")
print("BOTTOM 10 BY STAYED-TO-WATCH %")
print("========================================================")
for i, v in enumerate(by_stayed[-10:], 1):
    print(f"{i:2d}. {v['title'][:42]:<42} | Stayed: {v['stayed']:5.1f}% | APV: {v['apv']:5.1f}% | Views: {v['views']:5d} | Dur: {v['duration']}s")

# Top 15-20% (Top 6 videos) and Bottom 15-20% (Bottom 6 videos)
n_tier = int(len(data) * 0.18) # ~6 videos
top_tier = by_apv[:n_tier]
bottom_tier = by_apv[-n_tier:]

print(f"\n========================================================")
print(f"TOP {n_tier} PERFORMERS (TOP ~18%) SUMMARY")
print("========================================================")
print(f"Avg APV: {statistics.mean([x['apv'] for x in top_tier]):.2f}%")
print(f"Avg Stayed: {statistics.mean([x['stayed'] for x in top_tier]):.2f}%")
print(f"Avg Duration: {statistics.mean([x['duration'] for x in top_tier]):.1f}s")
print(f"Avg Views: {statistics.mean([x['views'] for x in top_tier]):.0f}")
print(f"Avg Subs Gained: {statistics.mean([x['subs_gained'] for x in top_tier]):.1f}")

print(f"\n========================================================")
print(f"BOTTOM {n_tier} PERFORMERS (BOTTOM ~18%) SUMMARY")
print("========================================================")
print(f"Avg APV: {statistics.mean([x['apv'] for x in bottom_tier]):.2f}%")
print(f"Avg Stayed: {statistics.mean([x['stayed'] for x in bottom_tier]):.2f}%")
print(f"Avg Duration: {statistics.mean([x['duration'] for x in bottom_tier]):.1f}s")
print(f"Avg Views: {statistics.mean([x['views'] for x in bottom_tier]):.0f}")
print(f"Avg Subs Gained: {statistics.mean([x['subs_gained'] for x in bottom_tier]):.1f}")

# Category Breakdown
print(f"\n========================================================")
print(f"CATEGORY PERFORMANCE BREAKDOWN")
print("========================================================")
cats = {}
for v in data:
    cats.setdefault(v["category"], []).append(v)

for cat, vlist in sorted(cats.items(), key=lambda x: statistics.mean([y['apv'] for y in x[1]]), reverse=True):
    avg_apv = statistics.mean([x['apv'] for x in vlist])
    avg_stayed = statistics.mean([x['stayed'] for x in vlist if x['stayed'] > 0])
    avg_views = statistics.mean([x['views'] for x in vlist])
    med_views = statistics.median([x['views'] for x in vlist])
    tot_views = sum([x['views'] for x in vlist])
    avg_dur = statistics.mean([x['duration'] for x in vlist])
    print(f"{cat:<30} (n={len(vlist):2d}) | Avg APV: {avg_apv:5.1f}% | Avg Stayed: {avg_stayed:5.1f}% | Med Views: {med_views:5.0f} | Tot Views: {tot_views:6d} | Avg Dur: {avg_dur:4.1f}s")

# Duration Breakdown
print(f"\n========================================================")
print(f"DURATION BRACKET BREAKDOWN")
print("========================================================")
dur_brackets = {
    "20-25s": [x for x in data if 20 <= x["duration"] <= 25],
    "26-30s": [x for x in data if 26 <= x["duration"] <= 30],
    "31-35s": [x for x in data if 31 <= x["duration"] <= 35],
    "36-40s": [x for x in data if 36 <= x["duration"] <= 40],
    "41s+": [x for x in data if x["duration"] > 40],
}
for bname, vlist in dur_brackets.items():
    if vlist:
        avg_apv = statistics.mean([x['apv'] for x in vlist])
        avg_stayed = statistics.mean([x['stayed'] for x in vlist if x['stayed'] > 0])
        med_views = statistics.median([x['views'] for x in vlist])
        tot_views = sum([x['views'] for x in vlist])
        print(f"{bname:<10} (n={len(vlist):2d}) | Avg APV: {avg_apv:5.1f}% | Avg Stayed: {avg_stayed:5.1f}% | Med Views: {med_views:5.0f} | Tot Views: {tot_views:6d}")

