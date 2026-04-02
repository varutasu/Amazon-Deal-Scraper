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

    @staticmethod
    def _deal_view(url, code=None):
        """Create a View with Amazon link and optional code display."""
        view = discord.ui.View()
        if url:
            view.add_item(discord.ui.Button(
                label="View on Amazon",
                url=url,
                style=discord.ButtonStyle.link,
                emoji="\U0001f6d2",
            ))
        return view

    def build_embed(self, deal, code=None):
        amz_url = affiliate_link(deal.get("amz_link", ""))
        discount_pct = self.parse_discount(deal.get("discount", "0"))
        title = deal.get("title", "Unknown Product")[:256]

        if discount_pct >= 80:
            color = 0xE74C3C
        elif discount_pct >= 60:
            color = 0xE67E22
        elif discount_pct >= 40:
            color = 0xF1C40F
        else:
            color = 0x2ECC71

        embed = discord.Embed(
            title=title,
            url=amz_url or None,
            color=color,
            timestamp=datetime.now(timezone.utc),
        )

        if deal.get("img_src"):
            embed.set_thumbnail(url=deal["img_src"])

        reg_price = deal.get("regular_price", "?")
        disc_price = deal.get("discounted_price", "?")
        embed.add_field(
            name="\U0001f4b0 Price",
            value=f"~~{reg_price}~~ \u2192 **{disc_price}**",
            inline=True,
        )
        embed.add_field(
            name="\U0001f525 Discount",
            value=f"**{discount_pct}% off**",
            inline=True,
        )
        embed.add_field(
            name="\U0001f4e6 Fulfillment",
            value=deal.get("fulfillment", "?"),
            inline=True,
        )

        if deal.get("shipping"):
            embed.add_field(name="\U0001f69a Shipping", value=str(deal["shipping"]), inline=True)
        if deal.get("review") and deal.get("review_count"):
            embed.add_field(
                name="\u2b50 Rating",
                value=f"{deal['review']} ({deal['review_count']} reviews)",
                inline=True,
            )
        if deal.get("category"):
            embed.add_field(name="\U0001f3f7\ufe0f Category", value=deal["category"], inline=True)

        resolved_code = code or deal.get("coupon_code")
        if resolved_code:
            if resolved_code.upper() == "DIRECTPRODUCT":
                embed.add_field(
                    name="\u2705 Promo Code",
                    value="Discount applied automatically at checkout",
                    inline=False,
                )
            else:
                embed.add_field(
                    name="\U0001f4cb Promo Code",
                    value=f"**`{resolved_code}`**",
                    inline=False,
                )

        embed.set_footer(text="PhantomCart \u2022 phantomcart.shop")

        return embed

    @staticmethod
    def _code_content(code):
        """Build message content with a copyable code block (Discord adds a Copy button)."""
        if not code:
            return None
        if code.upper() == "DIRECTPRODUCT":
            return "\u2705 **Discount applied automatically at checkout** \u2014 no code needed!"
        return (
            f"\U0001f381 **Promo Code \u2014 copy and apply at checkout:**\n"
            f"```\n{code}\n```"
        )

    async def post_deal_with_code(self, deal, code):
        """Post a deal WITH its code already resolved. Returns number of messages posted."""
        discount_pct = self.parse_discount(deal.get("discount", "0"))
        routes = await self.db.get_matching_deal_routes(discount_pct)

        amz_url = affiliate_link(deal.get("amz_link", ""))
        view = self._deal_view(amz_url)

        posted = 0
        for route in routes:
            channel = self.bot.get_channel(route["channel_id"])
            if not channel:
                continue
            try:
                embed = self.build_embed(deal, code=code)
                content = self._code_content(code)
                await channel.send(content=content, embed=embed, view=view)
                posted += 1
                await asyncio.sleep(0.3)
            except discord.Forbidden:
                print(f"[DealRouter] Missing permissions for #{channel.name} ({route['channel_id']})")
            except discord.HTTPException as e:
                print(f"[DealRouter] Failed to post to #{channel.name}: {e}")

        return posted
