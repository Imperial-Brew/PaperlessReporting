#!/usr/bin/env python
"""
Unified Interactive CLI for all Paperless Parts data pullers.

This script provides a single interface to run any of the available pullers
with interactive configuration of parameters.
"""

import asyncio
import argparse
import os
import sys
import signal
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

# Import pullers
from scripts.pull_quotes_async import QuotesPuller, main as quotes_main
from scripts.pull_orders_async import OrdersPuller, main as orders_main
from scripts.pull_accounts_async import AccountsPuller, main as accounts_main
from scripts.pull_contacts_async import ContactsPuller, main as contacts_main
from scripts.pull_users import UsersPuller, main as users_main
from scripts.utils.logging_config import configure_logging, get_logger
from scripts.utils.paperless_client import PaperlessPartsClient

# Configure logging
logger = get_logger(__name__)

# Constants
PID_FILE = os.path.join(os.path.dirname(__file__), "pull_runner.pid")
stop_requested = False


def signal_handler(sig, frame):
    """Handle interrupt signals."""
    global stop_requested
    logger.info("Interrupt received, stopping gracefully...")
    stop_requested = True


def save_pid():
    """Save the current process ID to a file."""
    with open(PID_FILE, 'w') as f:
        f.write(str(os.getpid()))


def remove_pid():
    """Remove the PID file."""
    if os.path.exists(PID_FILE):
        os.remove(PID_FILE)


class InteractivePullerCLI:
    """Interactive CLI for managing data pullers."""

    def __init__(self):
        self.settings: Dict[str, Any] = {
            "puller_type": "quotes",
            "start_id": 7500,
            "end_id": 7550,
            "log_level": "INFO",
            "include_revisions": True,
            "status_filter": None,
            "range_type": "start-stop",  # Options: "last-n", "start-stop", "all"
            "last_n": 50,
            "output_dir": "data_raw",
        }
        self.running = True
        configure_logging(level=self.settings["log_level"])
        self.max_ids = {
            "quotes": None,
            "orders": None,
            "accounts": None,
            "contacts": None,
            "users": None
        }

    async def get_max_id(self, entity_type: str) -> Optional[int]:
        """
        Get the maximum ID for a specific entity type.

        This method uses the /new endpoint to get the latest entity numbers.

        Args:
            entity_type: The type of entity (quotes, orders, etc.)

        Returns:
            The maximum ID for the entity type, or None if it couldn't be determined
        """
        # If we already have the max ID cached, return it
        if self.max_ids[entity_type] is not None:
            return self.max_ids[entity_type]

        client = PaperlessPartsClient()

        try:
            if entity_type == "quotes":
                # Get all quotes
                data = await client.get_quotes()
                if data and isinstance(data, list) and len(data) > 0:
                    # Check if there are any quotes with a number
                    quotes_with_number = [int(q["number"]) for q in data if q.get("number")]
                    if quotes_with_number:
                        max_id = max(quotes_with_number)
                        self.max_ids["quotes"] = max_id
                        logger.info(f"Determined maximum quote ID: {max_id}")
                        return max_id
                    else:
                        logger.warning("No quotes with valid numbers found")
                        return None

            elif entity_type == "orders":
                # Get all orders
                data = await client.get_orders()
                if data and isinstance(data, list) and len(data) > 0:
                    # Check if there are any orders with a number
                    orders_with_number = [int(o["number"]) for o in data if o.get("number")]
                    if orders_with_number:
                        max_id = max(orders_with_number)
                        self.max_ids["orders"] = max_id
                        logger.info(f"Determined maximum order ID: {max_id}")
                        return max_id
                    else:
                        logger.warning("No orders with valid numbers found")
                        return None

            # For other entity types, we don't have a direct way to get the max ID
            # We could implement a binary search or other approach if needed
            logger.warning(f"Getting max ID for {entity_type} is not implemented")
            return None

        except Exception as e:
            logger.error(f"Error getting max ID for {entity_type}: {str(e)}")
            return None

    def display_header(self):
        """Display the application header."""
        print("\n" + "=" * 60)
        print("  PAPERLESS PARTS DATA PULLER INTERACTIVE CLI")
        print("=" * 60)

    def display_menu(self):
        """Display the main menu options."""
        print("\nCURRENT SETTINGS:")
        print(f"  Puller Type: {self.settings['puller_type']}")

        if self.settings["range_type"] == "last-n":
            print(f"  Range: Last {self.settings['last_n']} items")
        elif self.settings["range_type"] == "start-stop":
            print(f"  ID Range: {self.settings['start_id']} - {self.settings['end_id']}")
        else:  # all
            print(f"  Range: All items")

        print(f"  Log Level: {self.settings['log_level']}")

        # Show puller-specific settings
        if self.settings["puller_type"] == "quotes":
            print(f"  Include Revisions: {self.settings['include_revisions']}")
            print(f"  Status Filter: {self.settings['status_filter'] or 'None'}")

        print(f"  Output Directory: {self.settings['output_dir']}")

        print("\nACTIONS:")
        print("  1. Change settings")
        print("  2. Start puller")
        print("  3. Stop running puller")
        print("  4. Check puller status")
        print("  5. Exit")

        return input("\nSelect an option (1-5): ")

    def validate_id_range(self) -> bool:
        """
        Validate that the start ID is less than or equal to the end ID.

        Returns:
            bool: True if valid, False otherwise
        """
        if self.settings["range_type"] != "start-stop":
            return True

        if self.settings["start_id"] > self.settings["end_id"]:
            print("\n⚠️ WARNING: Start ID is greater than End ID! ⚠️")
            print(f"  Current range: {self.settings['start_id']} - {self.settings['end_id']}")
            print("  This will result in no data being processed.")

            choice = input("\nWould you like to fix this now? (y/n): ").lower()
            if choice.startswith('y'):
                print("\n1. Change Start ID")
                print("2. Change End ID")
                fix_choice = input("\nSelect an option (1-2): ")

                if fix_choice == "1":
                    try:
                        new_start_id = int(input(f"Enter new Start ID (must be <= {self.settings['end_id']}): "))
                        if new_start_id <= self.settings["end_id"]:
                            self.settings["start_id"] = new_start_id
                            print(f"Start ID updated to {new_start_id}")
                            return True
                        else:
                            print("Invalid range. Start ID is still greater than End ID.")
                            return False
                    except ValueError:
                        print("Invalid input. Start ID must be an integer.")
                        return False

                elif fix_choice == "2":
                    try:
                        new_end_id = int(input(f"Enter new End ID (must be >= {self.settings['start_id']}): "))
                        if new_end_id >= self.settings["start_id"]:
                            self.settings["end_id"] = new_end_id
                            print(f"End ID updated to {new_end_id}")
                            return True
                        else:
                            print("Invalid range. End ID is still less than Start ID.")
                            return False
                    except ValueError:
                        print("Invalid input. End ID must be an integer.")
                        return False
                else:
                    print("Invalid choice.")
                    return False
            else:
                return False
        return True

    def change_settings(self):
        """Interactive menu to change puller settings."""
        print("\n--- CHANGE SETTINGS ---")
        print("  1. Puller Type")
        print("  2. Range Type")
        print("  3. Range Settings")
        print("  4. Log Level")
        print("  5. Puller-Specific Settings")
        print("  6. Output Directory")
        print("  7. Return to main menu")

        choice = input("\nSelect a setting to change (1-7): ")

        if choice == "1":
            print("\nAvailable puller types:")
            print("  1. quotes")
            print("  2. orders")
            print("  3. accounts")
            print("  4. contacts")
            print("  5. users")

            puller_choice = input("\nSelect puller type (1-5): ")
            puller_types = ["quotes", "orders", "accounts", "contacts", "users"]

            try:
                idx = int(puller_choice) - 1
                if 0 <= idx < len(puller_types):
                    self.settings["puller_type"] = puller_types[idx]
                else:
                    print("Invalid choice.")
            except ValueError:
                print("Invalid input. Please enter a number.")

        elif choice == "2":
            print("\nAvailable range types:")
            print("  1. Last N items")
            print("  2. Start-Stop range")
            print("  3. All items")

            range_choice = input("\nSelect range type (1-3): ")
            range_types = ["last-n", "start-stop", "all"]

            try:
                idx = int(range_choice) - 1
                if 0 <= idx < len(range_types):
                    self.settings["range_type"] = range_types[idx]
                else:
                    print("Invalid choice.")
            except ValueError:
                print("Invalid input. Please enter a number.")

        elif choice == "3":
            if self.settings["range_type"] == "last-n":
                try:
                    last_n = int(input("Enter number of items to pull: "))
                    if last_n > 0:
                        self.settings["last_n"] = last_n
                    else:
                        print("Invalid input. Number must be positive.")
                except ValueError:
                    print("Invalid input. Please enter a number.")

            elif self.settings["range_type"] == "start-stop":
                try:
                    start_id = int(input("Enter start ID: "))
                    self.settings["start_id"] = start_id
                except ValueError:
                    print("Invalid input. Start ID must be an integer.")

                try:
                    end_id = int(input("Enter end ID: "))
                    self.settings["end_id"] = end_id
                    # Validate ID range after changing end_id
                    self.validate_id_range()
                except ValueError:
                    print("Invalid input. End ID must be an integer.")

            elif self.settings["range_type"] == "all":
                print("No range settings needed for 'all' range type.")

        elif choice == "4":
            log_level = input("Enter log level (DEBUG/INFO/WARNING/ERROR): ").upper()
            if log_level in ["DEBUG", "INFO", "WARNING", "ERROR"]:
                self.settings["log_level"] = log_level
                configure_logging(level=log_level)
            else:
                print("Invalid log level.")

        elif choice == "5":
            if self.settings["puller_type"] == "quotes":
                print("\nQuotes puller settings:")
                print("  1. Include Revisions")
                print("  2. Status Filter")

                setting_choice = input("\nSelect setting to change (1-2): ")

                if setting_choice == "1":
                    include_revisions = input("Include revisions? (y/n): ").lower()
                    self.settings["include_revisions"] = include_revisions.startswith("y")

                elif setting_choice == "2":
                    status_options = ["None", "draft", "outstanding", "cancelled", "lost", "trash"]
                    print("Available status filters:")
                    for i, status in enumerate(status_options):
                        print(f"  {i}. {status}")

                    try:
                        status_choice = int(input("Select a status filter (0-5): "))
                        if 0 <= status_choice < len(status_options):
                            self.settings["status_filter"] = None if status_choice == 0 else status_options[status_choice]
                        else:
                            print("Invalid choice.")
                    except ValueError:
                        print("Invalid input. Please enter a number.")
            else:
                print(f"No specific settings available for {self.settings['puller_type']} puller.")

        elif choice == "6":
            output_dir = input("Enter output directory (default: data_raw): ")
            if output_dir:
                self.settings["output_dir"] = output_dir

    async def start_puller(self):
        """Start the puller with current settings."""
        # Validate ID range before starting
        if not self.validate_id_range():
            print("Puller not started due to invalid ID range.")
            return

        # Check if a puller is already running
        if os.path.exists(PID_FILE):
            try:
                with open(PID_FILE, 'r') as f:
                    pid = int(f.read().strip())
                try:
                    os.kill(pid, 0)  # Check if process exists
                    print(f"A puller is already running (PID: {pid})")
                    return
                except OSError:
                    # Process doesn't exist, remove stale PID file
                    print(f"Removing stale PID file for non-existent process {pid}")
                    remove_pid()
            except Exception as e:
                print(f"Error checking existing puller: {e}")
                remove_pid()

        # Register signal handlers
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        # Save PID
        save_pid()

        try:
            print(f"\nStarting {self.settings['puller_type']} puller...")

            # Determine start_id and end_id based on range_type
            start_id = None
            end_id = None

            if self.settings["range_type"] == "start-stop":
                start_id = self.settings["start_id"]
                end_id = self.settings["end_id"]
                print(f"Using ID range: {start_id} to {end_id}")
            elif self.settings["range_type"] == "last-n":
                # For last-n, we need to determine the current max ID and calculate start_id
                max_id = await self.get_max_id(self.settings["puller_type"])
                if max_id is not None:
                    end_id = max_id
                    start_id = max(1, end_id - self.settings["last_n"] + 1)
                    print(f"Pulling last {self.settings['last_n']} items")
                    print(f"Calculated ID range: {start_id} to {end_id}")
                else:
                    print(f"Could not determine max ID for {self.settings['puller_type']}")
                    print("Falling back to start-stop range")
                    start_id = self.settings["start_id"]
                    end_id = self.settings["end_id"]
                    print(f"Using ID range: {start_id} to {end_id}")
            else:  # all
                print("Pulling all items")

            # Run the appropriate puller
            if self.settings["puller_type"] == "quotes":
                # Override sys.argv for the quotes_main function
                sys.argv = [
                    "pull_quotes_async.py",
                    f"--start-id={start_id}" if start_id is not None else "",
                    f"--end-id={end_id}" if end_id is not None else "",
                    "--no-revisions" if not self.settings["include_revisions"] else "",
                    f"--status-filter={self.settings['status_filter']}" if self.settings["status_filter"] else "",
                    f"--log-level={self.settings['log_level']}",
                ]
                # Filter out empty strings
                sys.argv = [arg for arg in sys.argv if arg]

                await quotes_main()

            elif self.settings["puller_type"] == "orders":
                # Override sys.argv for the orders_main function
                sys.argv = [
                    "pull_orders_async.py",
                    f"--start-id={start_id}" if start_id is not None else "",
                    f"--end-id={end_id}" if end_id is not None else "",
                ]
                # Filter out empty strings
                sys.argv = [arg for arg in sys.argv if arg]

                await orders_main()

            elif self.settings["puller_type"] == "accounts":
                # Override sys.argv for the accounts_main function
                sys.argv = [
                    "pull_accounts_async.py",
                    # Add any specific parameters for accounts puller
                ]

                await accounts_main()

            elif self.settings["puller_type"] == "contacts":
                # Override sys.argv for the contacts_main function
                sys.argv = [
                    "pull_contacts_async.py",
                    # Add any specific parameters for contacts puller
                ]

                await contacts_main()

            elif self.settings["puller_type"] == "users":
                # Override sys.argv for the users_main function
                sys.argv = [
                    "pull_users.py",
                    # Add any specific parameters for users puller
                ]

                await users_main()

            print("Puller completed successfully")

        except Exception as e:
            print(f"Error running puller: {e}")
        finally:
            remove_pid()

    def stop_puller(self):
        """Stop a running puller."""
        if os.path.exists(PID_FILE):
            try:
                with open(PID_FILE, 'r') as f:
                    pid = int(f.read().strip())
                try:
                    os.kill(pid, signal.SIGTERM)
                    print(f"Sent termination signal to puller process (PID: {pid})")
                    remove_pid()
                    return True
                except OSError:
                    print(f"Process with PID {pid} not found, removing stale PID file")
                    remove_pid()
                    return False
            except Exception as e:
                print(f"Error stopping puller: {e}")
                return False
        else:
            print("No puller is currently running")
            return False

    def check_status(self):
        """Check if a puller is currently running."""
        if os.path.exists(PID_FILE):
            try:
                with open(PID_FILE, 'r') as f:
                    pid = int(f.read().strip())
                try:
                    os.kill(pid, 0)  # Check if process exists
                    print(f"Puller is running (PID: {pid})")
                except OSError:
                    print("No puller is currently running (stale PID file)")
                    remove_pid()
            except Exception as e:
                print(f"Error checking puller status: {e}")
        else:
            print("No puller is currently running")

    async def run(self):
        """Run the interactive CLI."""
        while self.running:
            self.display_header()
            choice = self.display_menu()

            if choice == "1":
                self.change_settings()

            elif choice == "2":
                await self.start_puller()
                input("\nPress Enter to continue...")

            elif choice == "3":
                self.stop_puller()
                input("\nPress Enter to continue...")

            elif choice == "4":
                self.check_status()
                input("\nPress Enter to continue...")

            elif choice == "5":
                print("Exiting...")
                self.running = False

            else:
                print("Invalid choice. Please select a number from 1-5.")
                input("\nPress Enter to continue...")


async def main():
    """
    Main entry point for the interactive CLI.
    """
    cli = InteractivePullerCLI()
    await cli.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nExiting due to user interrupt")
    except Exception as e:
        logger.error(f"Unhandled exception: {e}")
        sys.exit(1)
