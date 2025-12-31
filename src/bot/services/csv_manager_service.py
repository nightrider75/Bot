"""
CSV Manager Service - Universal CSV import/export for bot user data.

This service provides CSV upload and download functionality that works
with ANY user data provider (PostgreSQL, LocalCSV, InMemory).
"""

import csv
import io
import logging
from typing import Any, Dict
from uuid import UUID

from bot.bot_hub.hub import BotHub
from bot.models.bot_models import BotUserData

logger = logging.getLogger(__name__)


class CSVManagerService:
    """Universal CSV manager for bot user data."""

    @staticmethod
    async def export_users_to_csv(bot_id: UUID) -> str:
        """
        Export all bot users to CSV format.

        Works with any provider backend (PostgreSQL, LocalCSV, InMemory).

        Args:
            bot_id: UUID of the bot

        Returns:
            CSV content as string
        """
        bot_hub = BotHub(bot_id)

        # Get all user data from the provider (works with any backend)
        user_data_list = await bot_hub.userdata_provider.list_user_data()

        if not user_data_list:
            # Return empty CSV with headers
            return "user_id\n"

        # Collect all unique keys across all users
        all_keys = set()
        for user_data in user_data_list:
            all_keys.update(user_data.data.keys())

        # Sort keys for consistent column ordering
        sorted_keys = sorted(all_keys)

        # Create CSV in memory
        output = io.StringIO()
        fieldnames = ["user_id"] + sorted_keys
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()

        # Write rows
        for user_data in user_data_list:
            row = {"user_id": user_data.user_id}
            row.update(user_data.data)
            writer.writerow(row)

        csv_content = output.getvalue()
        logger.info(f"Exported {len(user_data_list)} users from bot {bot_id}")

        return csv_content

    @staticmethod
    async def import_users_from_csv(
        bot_id: UUID, csv_content: str, replace: bool = False
    ) -> Dict[str, Any]:
        """
        Import users from CSV content.

        Works with any provider backend (PostgreSQL, LocalCSV, InMemory).

        Args:
            bot_id: UUID of the bot
            csv_content: CSV content as string
            replace: If True, clears existing data before import

        Returns:
            Dictionary with import statistics
        """
        bot_hub = BotHub(bot_id)

        # Clear existing data if replace mode
        if replace:
            await bot_hub.userdata_provider.clear_user_data()
            logger.info(f"Cleared existing user data for bot {bot_id} (replace mode)")

        # Parse CSV
        csv_file = io.StringIO(csv_content)
        reader = csv.DictReader(csv_file)

        users_added = 0
        users_updated = 0
        errors = []

        for row_num, row in enumerate(
            reader, start=2
        ):  # start=2 because row 1 is headers
            try:
                user_id = row.get("user_id")
                if not user_id:
                    errors.append(f"Row {row_num}: Missing user_id")
                    continue

                # Remove user_id from data dict
                user_data_dict = {k: v for k, v in row.items() if k != "user_id"}

                # Check if user exists
                existing_data = await bot_hub.userdata_provider.get_user_data(user_id)

                # Create BotUserData object
                user_data = BotUserData(
                    bot_id=bot_id, user_id=user_id, data=user_data_dict
                )

                # Add to provider (will upsert)
                await bot_hub.userdata_provider.add_user_data([user_data])

                if existing_data is None:
                    users_added += 1
                else:
                    users_updated += 1

            except Exception as e:
                error_msg = f"Row {row_num}: {str(e)}"
                errors.append(error_msg)
                logger.error(error_msg)

        result = {
            "success": True,
            "users_added": users_added,
            "users_updated": users_updated,
            "total_processed": users_added + users_updated,
            "errors": errors,
            "error_count": len(errors),
        }

        logger.info(
            f"CSV import completed for bot {bot_id}: "
            f"{users_added} added, {users_updated} updated, {len(errors)} errors"
        )

        return result

    @staticmethod
    async def get_user_data_stats(bot_id: UUID) -> Dict[str, Any]:
        """
        Get statistics about bot user data.

        Args:
            bot_id: UUID of the bot

        Returns:
            Dictionary with statistics
        """
        bot_hub = BotHub(bot_id)
        user_data_list = await bot_hub.userdata_provider.list_user_data()

        # Calculate stats
        total_users = len(user_data_list)

        all_keys = set()
        for user_data in user_data_list:
            all_keys.update(user_data.data.keys())

        return {
            "total_users": total_users,
            "total_fields": len(all_keys),
            "field_names": sorted(all_keys),
        }

    @staticmethod
    async def delete_user(bot_id: UUID, user_id: str) -> bool:
        """
        Delete a specific user.

        Args:
            bot_id: UUID of the bot
            user_id: User identifier

        Returns:
            True if user was deleted, False if not found
        """
        bot_hub = BotHub(bot_id)

        # Check if user exists
        existing_data = await bot_hub.userdata_provider.get_user_data(user_id)

        if existing_data is None:
            return False

        await bot_hub.userdata_provider.delete_user_data(user_id)
        logger.info(f"Deleted user {user_id} from bot {bot_id}")

        return True

    @staticmethod
    async def clear_all_users(bot_id: UUID) -> int:
        """
        Clear all users for a bot.

        Args:
            bot_id: UUID of the bot

        Returns:
            Number of users deleted
        """
        bot_hub = BotHub(bot_id)

        # Get count before clearing
        user_data_list = await bot_hub.userdata_provider.list_user_data()
        user_count = len(user_data_list)

        # Clear all data
        await bot_hub.userdata_provider.clear_user_data()
        logger.info(f"Cleared {user_count} users from bot {bot_id}")

        return user_count
