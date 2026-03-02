"""
auth_forum Discord cog.

Registered via the discord_cogs_hook only when aadiscordbot is installed.
Provides a /forum slash command showing recent activity.

Requirements:
    pip install allianceauth-discordbot
    DISCORD_BOT_COGS must include this module, OR auth_forum registers it
    automatically via discord_cogs_hook in auth_hooks.py.
"""

import logging

logger = logging.getLogger(__name__)

try:
    import discord
    from discord.ext import commands
    from discord import SlashCommandGroup, Option

    class ForumCog(commands.Cog):
        """Alliance Auth Forum commands for Discord."""

        forum_group = SlashCommandGroup(
            name="forum",
            description="Alliance Auth Forum commands",
        )

        def __init__(self, bot):
            self.bot = bot

        @forum_group.command(
            name="recent",
            description="Show the 5 most recently active forum threads.",
        )
        async def recent_threads(self, ctx):
            """Return an embed listing the 5 most recently updated threads."""
            try:
                from auth_forum.models import Thread

                threads = (
                    Thread.objects.select_related("board", "author")
                    .order_by("-updated_at")[:5]
                )

                if not threads:
                    await ctx.respond("No threads found.", ephemeral=True)
                    return

                embed = discord.Embed(
                    title="🗨️  Recent Forum Activity",
                    color=discord.Color.blue(),
                )

                for t in threads:
                    author_name = t.author.username if t.author else "Unknown"
                    value = (
                        f"**Board:** {t.board.name}\n"
                        f"**Author:** {author_name}\n"
                        f"**Updated:** <t:{int(t.updated_at.timestamp())}:R>"
                    )
                    if t.is_locked:
                        value = "🔒 " + value
                    if t.is_pinned:
                        value = "📌 " + value
                    embed.add_field(
                        name=t.title[:256],
                        value=value,
                        inline=False,
                    )

                await ctx.respond(embed=embed)

            except Exception as exc:
                logger.exception("forum recent command failed: %s", exc)
                await ctx.respond(
                    "An error occurred fetching recent threads.",
                    ephemeral=True,
                )

        @forum_group.command(
            name="search",
            description="Search forum posts.",
        )
        async def search_posts(
            self,
            ctx,
            query: Option(str, "Search term", required=True),  # type: ignore[valid-type]
        ):
            """Search for posts containing the given term (returns top 5 results)."""
            try:
                from auth_forum.models import Post

                if len(query) < 3:
                    await ctx.respond(
                        "Search term must be at least 3 characters.", ephemeral=True
                    )
                    return

                results = Post.objects.filter(
                    content__icontains=query
                ).select_related("thread__board", "author").order_by("-created_at")[:5]

                if not results:
                    await ctx.respond(
                        f"No posts found matching **{query}**.", ephemeral=True
                    )
                    return

                embed = discord.Embed(
                    title=f"🔍  Forum Search: {query}",
                    color=discord.Color.blurple(),
                )

                for post in results:
                    author_name = post.author.username if post.author else "Unknown"
                    snippet = post.content[:200].replace("\n", " ")
                    if len(post.content) > 200:
                        snippet += "…"
                    embed.add_field(
                        name=post.thread.title[:256],
                        value=(
                            f"**Board:** {post.thread.board.name}\n"
                            f"**Author:** {author_name}\n"
                            f"_{snippet}_"
                        ),
                        inline=False,
                    )

                await ctx.respond(embed=embed)

            except Exception as exc:
                logger.exception("forum search command failed: %s", exc)
                await ctx.respond(
                    "An error occurred during search.", ephemeral=True
                )

    def setup(bot):
        bot.add_cog(ForumCog(bot))
        logger.info("auth_forum ForumCog loaded")

except ImportError:
    # aadiscordbot / py-cord is not installed — silently skip registration
    logger.debug(
        "auth_forum: discord library not available, ForumCog not loaded."
    )

    def setup(bot):
        pass
