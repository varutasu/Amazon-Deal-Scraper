import asyncio
from datetime import datetime, timezone

import discord

from Modules.Helper import affiliate_link


class DealRouter:
    """Posts scraped deals to Discord channels based on discount-range routes stored in MongoDB."""

    def __init__(self, bot, db_handler):
        self.bot = bot
        self.db = db_handler

    @staticmethod
    def parse_discount(raw):
        """Extract integer discount from strings like '85%', '-85', '85'."""
        cleaned = str(raw).replace("%", "").replace("-", "").strip()
        digits = "".join(c for c in cleaned if c.isdigit())
        return int(digits) if digits else 0

    def build_embed(self, deal):
        amz_url = affiliate_link(deal.get("amz_link", ""))
        discount_pct = self.parse_discount(deal.get("discount", "0"))
        title = deal.get("title", "Unknown Product")[:256]

        embed = discord.Embed(
            title=title,
            url=amz_url or None,
            color=0x2ECC71,
            timestamp=datetime.now(timezone.utc),
        )

        if deal.get("img_src"):
            embed.set_thumbnail(url=deal["img_src"])

        embed.add_field(
            name="Price",
            value=f"~~{deal.get('regular_price', '?')}~~ \u2192 **{deal.get('discounted_price', '?')}**",
            inline=True,
        )
        embed.add_field(name="Discount", value=f"**{discount_pct}% off**", inline=True)
        embed.add_field(name="Fulfillment", value=deal.get("fulfillment", "?"), inline=True)

        if deal.get("shipping"):
            embed.add_field(name="Shipping", value=str(deal["shipping"]), inline=True)
        if deal.get("review") and deal.get("review_count"):
            embed.add_field(
                name="Rating",
                value=f"\u2b50 {deal['review']} ({deal['review_count']} reviews)",
                inline=True,
            )
        if deal.get("category"):
            embed.add_field(name="Category", value=deal["category"], inline=True)

        return embed

    async def post_deal_to_routes(self, deal):
        """Find matching routes and post the deal to each channel. Returns number of channels posted to."""
        discount_pct = self.parse_discount(deal.get("discount", "0"))
        routes = await self.db.get_matching_deal_routes(discount_pct)

        posted = 0
        for route in routes:
            channel = self.bot.get_channel(route["channel_id"])
            if not channel:
                continue
            try:
                embed = self.build_embed(deal)
                await channel.send(embed=embed)
                posted += 1
                await asyncio.sleep(0.3)
            except discord.Forbidden:
                print(f"[DealRouter] Missing permissions for #{channel.name} ({route['channel_id']})")
            except discord.HTTPException as e:
                print(f"[DealRouter] Failed to post to #{channel.name}: {e}")

        return posted
