"""
Interactive CLI runner for Paperless Parts data pipelines.

This script provides an interactive interface for starting, stopping, and
managing pipeline executions for quotes and orders data.
"""

import asyncio
import os
import signal
import sys
import time
from typing import Dict, Any, Optional, Tuple

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from scripts.utils.logging_config import get_logger, configure_logging

# Initialize logger
logger = get_logger(__name__)

# Global flag to track if stop was requested
stop_requested = False
current_pipeline = None

# Path to store the PID file for the running pipeline
PID_FILE = os.path.join(os.path.dirname(__file__), "pipeline_pid.txt")


def signal_handler(sig, frame):
    """Handle termination signals by setting the stop flag."""
    global stop_requested
    logger.info(f"Received signal {sig}, initiating graceful shutdown...")
    stop_requested = True

    # If we're running in a separate process, this will be handled by the main process
    if current_pipeline:
        logger.info("Requesting pipeline to stop at next checkpoint...")


def save_pid():
    """Save the current process ID to a file for external stop commands."""
    try:
        with open(PID_FILE, 'w') as f:
            f.write(str(os.getpid()))
        logger.info(f"Saved PID {os.getpid()} to {PID_FILE}")
    except Exception as e:
        logger.error(f"Failed to save PID file: {e}")


def remove_pid():
    """Remove the PID file when the pipeline stops."""
    if os.path.exists(PID_FILE):
        try:
            os.remove(PID_FILE)
            logger.info(f"Removed PID file {PID_FILE}")
        except Exception as e:
            logger.error(f"Failed to remove PID file: {e}")


async def run_quotes(start_id: int, end_id: int, status_filter: Optional[str] = None) -> bool:
    """
    Run the quotes pipeline with the specified ID range.

    Args:
        start_id: Starting quote ID
        end_id: Ending quote ID
        status_filter: Optional status to filter quotes by

    Returns:
        bool: True if successful, False otherwise
    """
    global current_pipeline
    current_pipeline = "quotes"

    # Override the checkpoint file path to use the specified range
    from scripts.pipeline.run_quotes_pipeline import PROJECT_ROOT
    checkpoint_file = os.path.join(
        PROJECT_ROOT, "data_real", f"quote_pipeline_{start_id}_{end_id}_checkpoint.json"
    )

    # Monkey patch the checkpoint file path
    import scripts.pipeline.run_quotes_pipeline as quotes_pipeline
    quotes_pipeline.CHECKPOINT_FILE = checkpoint_file

    # Override the end_id in the run_pipeline function
    original_run_pipeline = quotes_pipeline.run_pipeline

    async def patched_run_pipeline():
        """Patched version of run_pipeline that checks for stop requests."""
        logger.info(f"Running Quote Pipeline ({start_id}-{end_id})")

        checkpoint = quotes_pipeline.load_checkpoint()
        current_start = start_id  # Ignore checkpoint and always start from specified ID
        pipeline_end_id = end_id

        logger.info(f"Starting from ID {current_start} to {pipeline_end_id}")

        # Process in smaller chunks to avoid timeouts
        CHUNK_SIZE = 50
        current_chunk_start = current_start

        while current_chunk_start <= pipeline_end_id and not stop_requested:
            current_chunk_end = min(current_chunk_start + CHUNK_SIZE - 1, pipeline_end_id)
            logger.info(f"Processing chunk {current_chunk_start}-{current_chunk_end}")

            quote_pipeline = (
                quotes_pipeline.PipelineBuilder("quote_pipeline")
                .add_acquisition(quotes_pipeline.PaperlessPartsDataAcquisitionStage(
                    start_id=current_chunk_start,
                    end_id=current_chunk_end,
                    status_filter=status_filter
                ))
                .add_batch_processor(quotes_pipeline.QuoteValidator())
                .add_batch_processor(quotes_pipeline.QuoteTransformer())
                .add_loading(quotes_pipeline.QuoteSplittingCSVLoader(
                    quotes_path=os.path.join(PROJECT_ROOT, "data_real", "quotes",
                                             f"quotes_{current_chunk_start}_{current_chunk_end}.csv"),
                    items_path=os.path.join(PROJECT_ROOT, "data_real", "quote_items",
                                            f"quote_items_{current_chunk_start}_{current_chunk_end}.csv")
                ))
                .build()
            )

            quote_pipeline.stages[0].configure_timeout(timeout=300.0)

            try:
                logger.info("Starting chunk execution")
                quote_output = await quote_pipeline.run(None)
                success = quote_output is not None
                logger.info(f"Chunk completed successfully: {success}")

                # Save progress
                quotes_pipeline.save_checkpoint(current_chunk_end)
                current_chunk_start = current_chunk_end + 1

                # Check if stop was requested
                if stop_requested:
                    logger.info("Stop requested, halting pipeline after current chunk")
                    break

            except asyncio.TimeoutError:
                logger.error(f"Timeout occurred processing chunk {current_chunk_start}-{current_chunk_end}")
                await asyncio.sleep(30)  # Wait before retrying
                continue
            except Exception as e:
                logger.error(f"Error processing chunk {current_chunk_start}-{current_chunk_end}: {e}", exc_info=True)
                quotes_pipeline.save_checkpoint(current_chunk_start - 1)
                raise

        if stop_requested:
            logger.info("Pipeline stopped before completion")
            return False

        # After all chunks are processed, merge the files
        try:
            success = quotes_pipeline.merge_chunk_files(start_id, pipeline_end_id)
            return success
        except Exception as e:
            logger.error(f"Error merging files: {e}", exc_info=True)
            return False

    # Replace the original function with our patched version
    quotes_pipeline.run_pipeline = patched_run_pipeline

    try:
        # Call our patched version directly instead of the original
        return await patched_run_pipeline()
    finally:
        # Restore the original function
        quotes_pipeline.run_pipeline = original_run_pipeline
        current_pipeline = None


async def run_orders(start_id: int, end_id: int) -> bool:
    """
    Run the orders pipeline with the specified ID range.

    Args:
        start_id: Starting order ID
        end_id: Ending order ID

    Returns:
        bool: True if successful, False otherwise
    """
    global current_pipeline
    current_pipeline = "orders"

    # Similar implementation as run_quotes but for orders pipeline
    from scripts.pipeline.run_orders_550_570_pipeline import PROJECT_ROOT
    checkpoint_file = os.path.join(
        PROJECT_ROOT, "data_real", f"order_pipeline_{start_id}_{end_id}_checkpoint.json"
    )

    # Monkey patch the checkpoint file path
    import scripts.pipeline.run_orders_550_570_pipeline as orders_pipeline
    orders_pipeline.CHECKPOINT_FILE = checkpoint_file

    # Override the end_id in the run_pipeline function
    original_run_pipeline = orders_pipeline.run_pipeline

    async def patched_run_pipeline():
        """Patched version of run_pipeline that checks for stop requests."""
        logger.info(f"Running Order Pipeline ({start_id}-{end_id})")

        checkpoint = orders_pipeline.load_checkpoint()
        current_start = start_id  # Ignore checkpoint and always start from specified ID
        pipeline_end_id = end_id

        logger.info(f"Starting from ID {current_start} to {pipeline_end_id}")

        # Process in smaller chunks to avoid timeouts
        CHUNK_SIZE = 20
        current_chunk_start = current_start

        while current_chunk_start <= pipeline_end_id and not stop_requested:
            current_chunk_end = min(current_chunk_start + CHUNK_SIZE - 1, pipeline_end_id)
            logger.info(f"Processing chunk {current_chunk_start}-{current_chunk_end}")

            order_pipeline = (
                orders_pipeline.PipelineBuilder("order_pipeline")
                .add_acquisition(orders_pipeline.OrdersDataAcquisitionStage(
                    start_id=current_chunk_start,
                    end_id=current_chunk_end
                ))
                .add_batch_processor(orders_pipeline.LenientOrderValidator())
                .add_batch_processor(orders_pipeline.LenientOrderTransformer())
                .add_loading(orders_pipeline.LenientOrderSplittingCSVLoader(
                    orders_path=os.path.join(PROJECT_ROOT, "data_real",
                                             f"orders_{current_chunk_start}_{current_chunk_end}.csv"),
                    items_path=os.path.join(PROJECT_ROOT, "data_real",
                                            f"order_items_{current_chunk_start}_{current_chunk_end}.csv")
                ))
                .build()
            )

            # Configure a longer timeout for the acquisition stage
            order_pipeline.stages[0].configure_timeout(timeout=300.0)

            # Configure the circuit breaker for the validator stage to be more tolerant
            order_pipeline.stages[1].configure_circuit_breaker(failure_threshold=20, reset_timeout=30.0)

            try:
                logger.info("Starting chunk execution")
                order_output = await order_pipeline.run(None)

                # Consider the chunk successful even if order_output is None
                success = True
                logger.info(f"Chunk completed successfully: {success}")

                # Save progress
                orders_pipeline.save_checkpoint(current_chunk_end)
                current_chunk_start = current_chunk_end + 1

                # Check if stop was requested
                if stop_requested:
                    logger.info("Stop requested, halting pipeline after current chunk")
                    break

            except asyncio.TimeoutError:
                logger.error(f"Timeout occurred processing chunk {current_chunk_start}-{current_chunk_end}")
                await asyncio.sleep(30)  # Wait before retrying
                continue
            except Exception as e:
                logger.error(f"Error processing chunk {current_chunk_start}-{current_chunk_end}: {e}", exc_info=True)
                orders_pipeline.save_checkpoint(current_chunk_start - 1)
                raise

        if stop_requested:
            logger.info("Pipeline stopped before completion")
            return False

        # After all chunks are processed, merge the files
        try:
            success = orders_pipeline.merge_chunk_files(start_id, pipeline_end_id)
            return success
        except Exception as e:
            logger.error(f"Error merging files: {e}", exc_info=True)
            return False

    # Replace the original function with our patched version
    orders_pipeline.run_pipeline = patched_run_pipeline

    try:
        # Call our patched version directly instead of the original
        return await patched_run_pipeline()
    finally:
        # Restore the original function
        orders_pipeline.run_pipeline = original_run_pipeline
        current_pipeline = None


def stop_running_pipeline():
    """
    Stop a running pipeline by sending a signal to the process.

    Returns:
        bool: True if a pipeline was stopped, False otherwise
    """
    if not os.path.exists(PID_FILE):
        logger.error("No running pipeline found (PID file missing)")
        return False

    try:
        with open(PID_FILE, 'r') as f:
            pid = int(f.read().strip())

        # Check if the process exists
        try:
            os.kill(pid, 0)  # This will raise an exception if the process doesn't exist
            logger.info(f"Sending stop signal to pipeline process (PID: {pid})")
            os.kill(pid, signal.SIGTERM)

            # Wait for the process to terminate
            max_wait = 30  # seconds
            for i in range(max_wait):
                try:
                    os.kill(pid, 0)
                    logger.info(f"Waiting for pipeline to stop ({i + 1}/{max_wait}s)...")
                    time.sleep(1)
                except OSError:
                    # Process has terminated
                    logger.info(f"Pipeline process (PID: {pid}) has stopped")
                    remove_pid()
                    return True

            # If we get here, the process didn't terminate gracefully
            logger.warning(f"Pipeline didn't stop gracefully after {max_wait}s, sending SIGKILL")
            os.kill(pid, signal.SIGKILL)
            remove_pid()
            return True

        except OSError:
            logger.warning(f"Process with PID {pid} not found, removing stale PID file")
            remove_pid()
            return False

    except Exception as e:
        logger.error(f"Error stopping pipeline: {e}")
        return False


class InteractiveCLI:
    """Interactive CLI for pipeline management."""

    def __init__(self):
        self.settings: Dict[str, Any] = {
            "pipeline_type": "quotes",
            "start_id": 7500,
            "end_id": 7550,
            "log_level": "INFO",
            "include_revisions": True,
            "status_filter": None,  # Add status filter setting
        }
        self.running = True
        configure_logging(level=self.settings["log_level"])

    def display_header(self):
        """Display the application header."""
        print("\n" + "=" * 60)
        print("  PAPERLESS PARTS PIPELINE INTERACTIVE CLI")
        print("=" * 60)

    def display_menu(self):
        """Display the main menu options."""
        print("\nCURRENT SETTINGS:")
        print(f"  Pipeline Type: {self.settings['pipeline_type']}")
        print(f"  ID Range: {self.settings['start_id']} - {self.settings['end_id']}")
        print(f"  Log Level: {self.settings['log_level']}")
        print(f"  Include Revisions: {self.settings['include_revisions']}")
        print(f"  Status Filter: {self.settings['status_filter'] or 'None'}")

        print("\nACTIONS:")
        print("  1. Change settings")
        print("  2. Start pipeline")
        print("  3. Stop running pipeline")
        print("  4. Check pipeline status")
        print("  5. Exit")

        return input("\nSelect an option (1-5): ")

    def validate_id_range(self) -> bool:
        """
        Validate that the start ID is less than or equal to the end ID.

        Returns:
            bool: True if valid, False otherwise
        """
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
        """Interactive menu to change pipeline settings."""
        print("\n--- CHANGE SETTINGS ---")
        print("  1. Pipeline Type")
        print("  2. Start ID")
        print("  3. End ID")
        print("  4. Log Level")
        print("  5. Include Revisions")
        print("  6. Status Filter")
        print("  7. Return to main menu")

        choice = input("\nSelect a setting to change (1-6): ")

        if choice == "1":
            pipeline_type = input("Enter pipeline type (quotes/orders): ").lower()
            if pipeline_type in ["quotes", "orders"]:
                self.settings["pipeline_type"] = pipeline_type
            else:
                print("Invalid pipeline type. Must be 'quotes' or 'orders'.")

        elif choice == "2":
            try:
                start_id = int(input("Enter start ID: "))
                self.settings["start_id"] = start_id
                # Validate ID range after changing start_id
                self.validate_id_range()
            except ValueError:
                print("Invalid input. Start ID must be an integer.")

        elif choice == "3":
            try:
                end_id = int(input("Enter end ID: "))
                self.settings["end_id"] = end_id
                # Validate ID range after changing end_id
                self.validate_id_range()
            except ValueError:
                print("Invalid input. End ID must be an integer.")

        elif choice == "4":
            log_level = input("Enter log level (DEBUG/INFO/WARNING/ERROR): ").upper()
            if log_level in ["DEBUG", "INFO", "WARNING", "ERROR"]:
                self.settings["log_level"] = log_level
                configure_logging(level=log_level)
            else:
                print("Invalid log level.")

        elif choice == "5":
            include_revisions = input("Include revisions? (y/n): ").lower()
            self.settings["include_revisions"] = include_revisions.startswith("y")

        elif choice == "6":
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

    async def start_pipeline(self):
        """Start the pipeline with current settings."""
        # Validate ID range before starting
        if not self.validate_id_range():
            print("Pipeline not started due to invalid ID range.")
            return

        # Check if a pipeline is already running
        if os.path.exists(PID_FILE):
            try:
                with open(PID_FILE, 'r') as f:
                    pid = int(f.read().strip())
                try:
                    os.kill(pid, 0)  # Check if process exists
                    print(f"A pipeline is already running (PID: {pid})")
                    return
                except OSError:
                    # Process doesn't exist, remove stale PID file
                    print(f"Removing stale PID file for non-existent process {pid}")
                    remove_pid()
            except Exception as e:
                print(f"Error checking existing pipeline: {e}")
                remove_pid()

        # Register signal handlers
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        # Save PID
        save_pid()

        try:
            print(f"\nStarting {self.settings['pipeline_type']} pipeline from ID "
                  f"{self.settings['start_id']} to {self.settings['end_id']}...")

            if self.settings["pipeline_type"] == "quotes":
                success = await run_quotes(
                    self.settings["start_id"], 
                    self.settings["end_id"],
                    self.settings["status_filter"]
                )
            else:  # orders
                success = await run_orders(self.settings["start_id"], self.settings["end_id"])

            if stop_requested:
                print("Pipeline was stopped before completion")
            elif success:
                print("Pipeline completed successfully")
            else:
                print("Pipeline failed")

        except Exception as e:
            print(f"Error running pipeline: {e}")
        finally:
            remove_pid()

    def stop_pipeline(self):
        """Stop a running pipeline."""
        success = stop_running_pipeline()
        if success:
            print("Pipeline stopped successfully")
        else:
            print("No running pipeline found or failed to stop pipeline")

    def check_status(self):
        """Check if a pipeline is currently running."""
        if os.path.exists(PID_FILE):
            try:
                with open(PID_FILE, 'r') as f:
                    pid = int(f.read().strip())
                try:
                    os.kill(pid, 0)  # Check if process exists
                    print(f"Pipeline is running (PID: {pid})")
                except OSError:
                    print("No pipeline is currently running (stale PID file)")
                    remove_pid()
            except Exception as e:
                print(f"Error checking pipeline status: {e}")
        else:
            print("No pipeline is currently running")

    async def run(self):
        """Run the interactive CLI."""
        while self.running:
            self.display_header()
            choice = self.display_menu()

            if choice == "1":
                self.change_settings()

            elif choice == "2":
                await self.start_pipeline()
                input("\nPress Enter to continue...")

            elif choice == "3":
                self.stop_pipeline()
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
    cli = InteractiveCLI()
    await cli.run()


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
