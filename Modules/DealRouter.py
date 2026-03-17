import asyncio
from datetime import datetime, timezone

import discord

from Modules.Helper import affiliate_link


class DealRouter:
    """Posts scraped deals to Discord channels based on discount-range routes stored in MongoDB."""

    PENDING_CODE_TEXT = "\u23f3 Fetching code..."

    def __init__(self, bot, db_handler):
        self.bot = bot
        self.db = db_handler

    @staticmethod
    def parse_discount(raw):
        """Extract integer discount from strings like '85%', '-85', '85'."""
        cleaned = str(raw).replace("%", "").replace("-", "").strip()
        digits = "".join(c for c in cleaned if c.isdigit())
        return int(digits) if digits else 0

    def build_embed(self, deal, code_status="pending"):
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

        if deal.get("coupon_code"):
            embed.add_field(
                name="Promo Code",
                value=f"```\n{deal['coupon_code']}\n```",
                inline=False,
            )
        elif code_status == "pending":
            embed.add_field(
                name="Promo Code",
                value=self.PENDING_CODE_TEXT,
                inline=False,
            )
        else:
            embed.add_field(
                name="Promo Code",
                value="Unavailable — use `/search_with_keywords` to claim",
                inline=False,
            )

        return embed

    async def post_deal_to_routes(self, deal, code_status="pending"):
        """Post deal to matching channels. Returns list of (channel_id, message_id) tuples."""
        discount_pct = self.parse_discount(deal.get("discount", "0"))
        routes = await self.db.get_matching_deal_routes(discount_pct)

        posted_messages = []
        for route in routes:
            channel = self.bot.get_channel(route["channel_id"])
            if not channel:
                continue
            try:
                embed = self.build_embed(deal, code_status=code_status)
                msg = await channel.send(embed=embed)
                posted_messages.append((channel.id, msg.id))
                await asyncio.sleep(0.3)
            except discord.Forbidden:
                print(f"[DealRouter] Missing permissions for #{channel.name} ({route['channel_id']})")
            except discord.HTTPException as e:
                print(f"[DealRouter] Failed to post to #{channel.name}: {e}")

        return posted_messages

    async def edit_message_with_code(self, channel_id, message_id, code):
        """Edit a previously posted deal message to add the promo code."""
        channel = self.bot.get_channel(channel_id)
        if not channel:
            return False
        try:
            msg = await channel.fetch_message(message_id)
            if not msg.embeds:
                return False

            embed = msg.embeds[0].copy()
            for i, field in enumerate(embed.fields):
                if field.name == "Promo Code":
                    if code:
                        embed.set_field_at(i, name="Promo Code", value=f"```\n{code}\n```", inline=False)
                    else:
                        embed.set_field_at(
                            i, name="Promo Code",
                            value="Unavailable \u2014 use `/search_with_keywords` to claim",
                            inline=False,
                        )
                    break

            await msg.edit(embed=embed)
            return True
        except (discord.NotFound, discord.Forbidden, discord.HTTPException) as e:
            print(f"[DealRouter] Failed to edit message {message_id}: {e}")
            return False
