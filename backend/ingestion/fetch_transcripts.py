"""
Fetch transcripts from Lenny's Podcast GitHub repository.

Source: https://github.com/Yash-Kavaiya/Lenny-s-podcast-transcripts
Alternative: Any publicly available Lenny transcript repo

Usage:
    python -m ingestion.fetch_transcripts
    python -m ingestion.fetch_transcripts --limit 20
"""
import argparse
import logging
import sys
import time
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).parent.parent))
from app.config import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

# Primary transcript source: GitHub raw files
GITHUB_API = "https://api.github.com/repos/Yash-Kavaiya/Lenny-s-podcast-transcripts/contents/"
GITHUB_RAW = "https://raw.githubusercontent.com/Yash-Kavaiya/Lenny-s-podcast-transcripts/main/"

HEADERS = {
    "Accept": "application/vnd.github.v3+json",
    "User-Agent": "LennyGrowthAssistant/1.0",
}


def fetch_file_list(limit: int = 50) -> list[dict]:
    """Fetch list of transcript files from the GitHub repo."""
    try:
        with httpx.Client(timeout=30.0) as client:
            r = client.get(GITHUB_API, headers=HEADERS)
            r.raise_for_status()
            files = [
                f for f in r.json()
                if f.get("type") == "file" and f["name"].endswith(".txt")
            ]
            logger.info("Found %d transcript files in repo", len(files))
            return files[:limit]
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 403:
            logger.error("GitHub API rate limit hit. Use --token or wait.")
        raise
    except Exception as e:
        logger.error("Failed to fetch file list: %s", e)
        raise


def fetch_transcript(file_info: dict, output_dir: Path) -> bool:
    """Download a single transcript file. Returns True if saved."""
    filename = file_info["name"]
    out_path = output_dir / filename

    if out_path.exists():
        logger.info("Already exists: %s — skipping", filename)
        return False

    raw_url = file_info.get("download_url") or f"{GITHUB_RAW}{filename}"

    try:
        with httpx.Client(timeout=30.0) as client:
            r = client.get(raw_url, headers=HEADERS)
            r.raise_for_status()
            out_path.write_text(r.text, encoding="utf-8")
            logger.info("Downloaded: %s (%d chars)", filename, len(r.text))
            return True
    except Exception as e:
        logger.error("Failed to download %s: %s", filename, e)
        return False


def create_sample_transcripts(output_dir: Path):
    """
    Create sample transcript files for demonstration when network is unavailable.
    These are representative synthetic excerpts matching Lenny's content style.
    """
    samples = [
        (
            "ep001_superhuman_product_market_fit.txt",
            """Lenny's Podcast - Episode 1: How Superhuman Built an Engine to Find Product-Market Fit
Host: Lenny Rachitsky | Guest: Rahul Vohra, CEO of Superhuman

[Transcript begins]

Lenny: Welcome to the show. Today I'm talking with Rahul Vohra, the CEO and co-founder of Superhuman. Rahul, welcome.

Rahul: Thanks for having me, Lenny. Excited to dig into this.

Lenny: So let's start with product-market fit. You've written one of the most cited essays on how to measure it. Walk me through the framework.

Rahul: Sure. The fundamental question is: how disappointed would your users be if they could no longer use your product? We survey users and ask them to pick one of four options: very disappointed, somewhat disappointed, not disappointed, or don't care.

The key insight is this: if more than 40% of your users say they'd be very disappointed without your product, you have product-market fit. Below 40%, you don't.

Lenny: Where did that 40% number come from?

Rahul: Empirically. We benchmarked it across hundreds of startups. Companies with strong product-market fit — the Slacks, the Dropboxes of the world — consistently scored above 40%. Companies that struggled, that eventually died, scored below.

Lenny: And Superhuman was at 22% when you started this process?

Rahul: That's right. And here's the critical mistake most founders make: they look at that low score and think they need to make everyone happy. Wrong. You look at the people who said "very disappointed" and you ask: who are they? What do they love? And equally important — what do the "somewhat disappointed" people wish the product had?

Lenny: Talk me through how you actually used the survey responses.

Rahul: We'd ask three follow-up questions. First: what type of person do you think would most benefit from Superhuman? Second: what's the main benefit you get from it? Third: what would help you get more out of it?

The "very disappointed" segment told us: the main benefit was speed. They were busy professionals who had hundreds of emails a day and felt drowning. Speed was the product promise.

The "somewhat disappointed" segment often said they wanted mobile support. But here's where judgment matters — you can't build for everyone. We decided to deepen the value for our core segment rather than broaden for the periphery.

Lenny: How did that change the product?

Rahul: We doubled down on speed. Every feature we built had to make the product faster. We introduced keyboard shortcuts that let you process email ten times faster than Gmail. We built "Superhuman AI" to help you write faster. Everything centered on the core promise.

The 22% went to 58% in about a year. That's how we found product-market fit.

Lenny: What's the most common mistake you see founders make with this?

Rahul: Confusing retention with product-market fit. You can have a sticky product people use out of habit without having a product they truly love. The survey cuts through that. It's asking about genuine disappointment — the kind that would make someone switch.

Also: not segmenting. If you ask everyone the survey question and average the results, you'll get a muddled answer. Segment by role, by use case, by acquisition channel. The signal is often buried in a specific cohort.

Lenny: Before we close — one tactical thing founders can do this week?

Rahul: Send the survey. Even if you have 100 users. The data you get will be worth more than a month of strategy sessions. And ask the follow-up questions — the quantitative score is just the start. The qualitative answers are where the insights live.

[Transcript ends]
""",
        ),
        (
            "ep002_growth_loops_not_funnels.txt",
            """Lenny's Podcast - Episode 2: Why Growth Loops Beat Funnels Every Time
Host: Lenny Rachitsky | Guest: Brian Balfour, CEO of Reforge

[Transcript begins]

Lenny: Brian, I've heard you say that funnels are the wrong mental model for growth. That's a bold claim. Make your case.

Brian: The funnel model has served us for decades, but it has a fundamental flaw: it's linear. Input goes in the top, output comes out the bottom. It doesn't capture how the best products in the world actually grow.

A growth loop is cyclical. The output of one user cycle becomes the input for acquiring the next user. That's compounding. That's how you get exponential growth instead of linear growth.

Lenny: Give me a concrete example.

Brian: Let's take Dropbox. User signs up. They invite a friend to share a folder. That friend signs up. They invite another friend. Each user cycle produces new users. The referral loop compounds over time.

Or take a marketplace like eBay in the early days. Seller lists an item. Buyer finds it, purchases. That successful transaction causes the seller to list more items and the buyer to come back. Supply and demand feed each other. That's a loop.

Lenny: And a funnel doesn't capture that?

Brian: Not at all. A funnel says: we got X users from ads, Y% converted, Z% retained. Full stop. There's no mechanism for those Z% to go out and generate more users. You have to refuel the top of the funnel every single time.

Lenny: How do you identify your growth loop?

Brian: Three questions. One: what is the output of a user engaging with your product? Two: can that output become an input to acquiring another user? Three: is there a mechanism that connects those two?

For a social product, the output is content. That content gets shared. Sharing brings in new users. Loop closed.

For a B2B SaaS product, the output might be work artifacts — documents, reports. If those artifacts get shared with non-users, you have a viral loop. Think Calendly, DocuSign.

Lenny: What about products where it's not obvious?

Brian: Most products have a latent loop that founders haven't activated yet. Take a CRM. Salespeople use it. They create data. That data could be analyzed and turned into industry benchmarks. Benchmarks attract prospects. Prospects become users.

The question is always: what is the natural byproduct of my users using my product, and can that byproduct recruit more users?

Lenny: How does this change how you build?

Brian: Fundamentally. In a funnel model, you optimize each stage independently. In a loop model, you optimize the cycle. You ask: how do I make the loop spin faster? How do I make it wider? How do I add more loops?

Faster: reduce friction at every step. Wider: increase the conversion rate of output to input. More loops: add new ways users recruit users.

Lenny: Favorite example of a company that nailed this?

Brian: Slack. Think about it. Someone uses Slack. They invite their colleagues. The colleagues integrate their tools — GitHub, Jira. Those integrations produce notifications in Slack. Those notifications bring those tool users into Slack. The more integrated Slack is, the stickier and more referral-rich it becomes.

Lenny: Takeaway for founders?

Brian: Map your loop before you build your next feature. Draw it on a whiteboard. If you can't close the loop, you're building a feature, not a growth system.

[Transcript ends]
""",
        ),
        (
            "ep003_north_star_metric.txt",
            """Lenny's Podcast - Episode 3: Finding Your North Star Metric
Host: Lenny Rachitsky | Guest: Shishir Mehrotra, CEO of Coda

[Transcript begins]

Lenny: Shishir, you've led product at YouTube and now built Coda. You've thought a lot about metrics. What's a North Star Metric and why does it matter?

Shishir: A North Star Metric is the single number that best captures the core value your product delivers to customers. It's not a business metric like revenue — it's a product metric that, when it grows, revenue follows.

For YouTube, it was watch time. Every decision — what to recommend, how to rank, what creators to support — could be evaluated through that lens. Does this increase watch time? Then it's probably good. Does it decrease watch time? Probably not.

Lenny: Why not just use revenue?

Shishir: Revenue is a lagging indicator. It tells you what happened, not what's happening. By the time revenue changes, the product decisions that drove it are months in the past. You've already made twelve more decisions on top of wrong assumptions.

A North Star is a leading indicator. When users find more value, they use the product more, which eventually drives revenue. But you can observe the usage signal in real-time.

Lenny: How do you find your North Star?

Shishir: Start with this question: what is the moment when a user gets genuine value from your product? Not account creation. Not first login. The moment they go "oh, this is actually useful."

For Slack, that moment is when a team sends 2,000 messages. They've found it valuable enough to commit. Slack famously measured that as their activation threshold.

For Airbnb, it's the first successful stay — both parties transacted and it went well.

Lenny: And the metric captures that?

Shishir: Ideally it's a rate or frequency of that moment happening across your user base. "Number of teams sending 2,000 messages in their first month." That's more actionable than "number of users."

Lenny: What are the failure modes?

Shishir: Three big ones. First: vanity metrics. Total registered users is a vanity metric. Anyone can inflate it. It doesn't capture value. Second: gaming. If your North Star is a number, people will optimize for the number, not the behavior. Choose a metric that's hard to game. Watch time, not clicks.

Third: too many North Stars. I've seen companies with five North Star Metrics. That's not a North Star — that's a sky full of stars. You can't navigate by it. The whole point is to have one.

Lenny: What's Coda's?

Shishir: Docs that get used. A Coda doc that someone creates but never shares — that's not value delivered. A doc that a team uses every day to run their meetings, track their projects — that's value. So we measure active, collaborative docs.

Lenny: Any advice for founders trying to find theirs?

Shishir: Look at your best customers — the ones who would be devastated if you shut down. What do they have in common? What behavior do they all exhibit? That behavior is probably your North Star.

Then test it: does it correlate with retention? With expansion revenue? If your best customers are the ones where this metric is highest, you've found something real.

[Transcript ends]
""",
        ),
        (
            "ep004_pricing_strategy_for_saas.txt",
            """Lenny's Podcast - Episode 4: Pricing Strategy for SaaS Products
Host: Lenny Rachitsky | Guest: Patrick Campbell, Founder of ProfitWell

[Transcript begins]

Lenny: Patrick, you've analyzed pricing data from thousands of SaaS companies. What's the single biggest mistake you see?

Patrick: Underpricing. By a huge margin. The average SaaS company has raised prices maybe once in its history, and the last time was probably three years ago. Meanwhile they've added features, found better customers, created more value — and their price reflects none of that.

Lenny: Why does underpricing happen?

Patrick: Fear. Founders are terrified of losing customers. They think a price increase will cause a churn spike. The data says otherwise. When we've surveyed customers who churned, price is almost never the real reason. They churn because they didn't get value. Fix value, and you can charge more.

Lenny: Walk me through how to think about pricing.

Patrick: Start with willingness to pay research. You want to ask customers: "At what price does this product become too expensive?" and "At what price does this product seem too cheap to be trustworthy?" The intersection gives you your acceptable price range.

Then you look at your value metric — the one thing that scales with how much value a customer gets. For a CRM, it might be number of contacts. For a communication tool, number of seats. For a usage-based product, API calls.

Your pricing should scale with your value metric.

Lenny: What about freemium versus free trial?

Patrick: Freemium works when you have viral acquisition, low marginal cost of serving a free user, and a clear upgrade trigger. Think Spotify, Dropbox.

Free trial works better for products with high setup costs, enterprise sales motion, or where the "aha moment" requires some configuration. The time limit creates urgency.

The mistake is defaulting to freemium because it feels growth-friendly. It's a product decision, not a growth hack.

Lenny: Packaging — how should founders think about tiers?

Patrick: Three tiers is optimal in almost every case. Starter, Growth, Enterprise. The Starter tier exists to get people in the door and let them discover value. Growth is your sweet spot — where most revenue comes from. Enterprise is for customization and security buyers.

The middle tier should contain the features that 80% of your customers actually need. Too often founders put the good features in Enterprise and then wonder why nobody upgrades to Growth.

Lenny: One thing a founder should do differently about pricing?

Patrick: Raise prices. Now. If you haven't changed your pricing in a year and you've shipped meaningful features, you're leaving money on the table. Start by raising prices 15-20% on new customers only. Watch what happens to conversion. I'd bet it stays flat or improves — because the customers who care most about price are often your worst customers.

[Transcript ends]
""",
        ),
        (
            "ep005_retention_and_churn.txt",
            """Lenny's Podcast - Episode 5: The Science of Retention
Host: Lenny Rachitsky | Guest: Casey Winters, Chief Product Officer

[Transcript begins]

Lenny: Casey, you've worked on retention at Pinterest, Grubhub, Eventbrite. What do most companies get wrong?

Casey: They treat retention as a metric to track instead of a behavior to design. They look at monthly retention numbers, panic when they go down, ship a retention campaign, and move on. They're reacting rather than building.

Retention is built in the product from day one. It's about what happens in the first minute, the first session, the first week. If those go wrong, no re-engagement email will fix it.

Lenny: Talk me through the framework.

Casey: I think about retention in three phases. Immediate retention — does the user come back within 24 hours? Short-term retention — do they come back in the first month? Long-term retention — do they have a reason to come back six months from now?

Most companies focus on long-term and ignore immediate. But if someone doesn't come back in 24 hours after signing up, they almost never come back long-term. You've lost them.

Lenny: What's driving immediate retention?

Casey: Expectation matching and the "aha moment." Did the product deliver what the marketing promised? Did they find the core value fast enough?

For Pinterest, the aha moment was saving your first five pins. If you didn't do that in your first session, you didn't come back. So every product decision in onboarding was about getting people to save five pins.

Lenny: How do you find your aha moment?

Casey: Cohort analysis. Take your retained users — say, people who came back 30 days later. What did they do in their first session that churned users didn't? Look for statistically significant behaviors.

The answer is usually obvious once you see it. It's almost always core product action performed above a certain threshold within a certain time window.

Lenny: What about long-term retention?

Casey: Habit formation. You need to build the product into the user's routine. The tools for this are: frequency (use it more often), integration (connect it to things people already do), and notifications (bring them back).

But notifications are a trap. Over-notification is one of the fastest ways to teach users to ignore you. Every notification should deliver value. If it doesn't, cut it.

Lenny: Tactical advice for a startup with a retention problem?

Casey: Talk to churned users. Not with a survey — with a phone call. Ask them what the last thing they did in the product was, and why they stopped. The answer is almost always something you didn't expect.

And then talk to your most retained users. What's their routine? What would break in their life if you went away? The delta between those two groups is your product roadmap.

[Transcript ends]
""",
        ),
    ]

    output_dir.mkdir(parents=True, exist_ok=True)
    created = 0
    for filename, content in samples:
        path = output_dir / filename
        if not path.exists():
            path.write_text(content, encoding="utf-8")
            logger.info("Created sample transcript: %s", filename)
            created += 1

    if created:
        logger.info("Created %d sample transcripts in %s", created, output_dir)
    else:
        logger.info("Sample transcripts already exist")

    return created


def main():
    parser = argparse.ArgumentParser(description="Fetch Lenny's Podcast transcripts")
    parser.add_argument("--limit", type=int, default=20, help="Max transcripts to fetch")
    parser.add_argument("--samples-only", action="store_true",
                        help="Create local sample transcripts without network requests")
    parser.add_argument("--output-dir", type=str, default=settings.TRANSCRIPTS_DIR)
    args = parser.parse_args()

    output_dir = Path(args.output_dir)

    if args.samples_only:
        create_sample_transcripts(output_dir)
        return

    # Try fetching from GitHub
    logger.info("Fetching transcripts from GitHub (limit: %d)", args.limit)
    try:
        files = fetch_file_list(args.limit)
        downloaded = 0
        for i, file_info in enumerate(files):
            if fetch_transcript(file_info, output_dir):
                downloaded += 1
            if i > 0 and i % 10 == 0:
                # Respect GitHub rate limits
                logger.info("Pause to respect rate limits...")
                time.sleep(1)
        logger.info("Downloaded %d transcripts", downloaded)
    except Exception as e:
        logger.warning("Network fetch failed: %s — falling back to sample transcripts", e)
        create_sample_transcripts(output_dir)


if __name__ == "__main__":
    main()
