#!/usr/bin/env python3
"""
Admin Setup Script
==================
Interactive script to promote a player to admin or manage admin roles.
"""
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from models.player import Player
from models.data_store import init_data_store
from config import Config


def display_menu():
    """Display main menu"""
    print("\n" + "=" * 50)
    print("  Mini Golf Leaderboard - Admin Setup")
    print("=" * 50)
    print("\n1. Promote player to admin")
    print("2. Demote admin to player")
    print("3. List all admins")
    print("4. List all players")
    print("5. Exit")
    print()


def list_players(players, title="All Players"):
    """Display list of players"""
    if not players:
        print(f"\n  No {title.lower()} found.")
        return

    print(f"\n{title}:")
    print("-" * 80)
    print(f"{'#':<4} {'Name':<25} {'Email':<30} {'Role':<10} {'Linked':<8}")
    print("-" * 80)

    for idx, player in enumerate(players, 1):
        name = player['name']
        email = player.get('email', '')
        role = player.get('role', 'player')
        linked = 'Yes' if player.get('google_id') else 'No'
        print(f"{idx:<4} {name:<25} {email:<30} {role:<10} {linked:<8}")

    print("-" * 80)


def promote_to_admin():
    """Promote a player to admin"""
    players = Player.get_all(active_only=True)
    non_admins = [p for p in players if p.get('role', 'player') != 'admin']

    if not non_admins:
        print("\n  All active players are already admins!")
        return

    list_players(non_admins, "Players (Non-Admins)")

    try:
        selection = int(input("\nEnter player number to promote to admin (0 to cancel): "))

        if selection == 0:
            print("  Cancelled.")
            return

        if selection < 1 or selection > len(non_admins):
            print("  Invalid selection.")
            return

        player = non_admins[selection - 1]
        confirm = input(f"\nPromote '{player['name']}' to admin? (yes/no): ").lower()

        if confirm == 'yes':
            success, message = Player.update(player['id'], role='admin')
            if success:
                print(f"\n  ✓ {player['name']} has been promoted to admin!")
            else:
                print(f"\n  ✗ Error: {message}")
        else:
            print("  Cancelled.")

    except ValueError:
        print("  Invalid input. Please enter a number.")
    except Exception as e:
        print(f"  Error: {e}")


def demote_to_player():
    """Demote an admin to player"""
    players = Player.get_all(active_only=True)
    admins = [p for p in players if p.get('role', 'player') == 'admin']

    if not admins:
        print("\n  No admins found!")
        return

    list_players(admins, "Current Admins")

    if len(admins) == 1:
        print("\n  Warning: This is the only admin. Consider promoting another player first.")

    try:
        selection = int(input("\nEnter admin number to demote to player (0 to cancel): "))

        if selection == 0:
            print("  Cancelled.")
            return

        if selection < 1 or selection > len(admins):
            print("  Invalid selection.")
            return

        player = admins[selection - 1]
        confirm = input(f"\nDemote '{player['name']}' to player? (yes/no): ").lower()

        if confirm == 'yes':
            success, message = Player.update(player['id'], role='player')
            if success:
                print(f"\n  ✓ {player['name']} has been demoted to player.")
            else:
                print(f"\n  ✗ Error: {message}")
        else:
            print("  Cancelled.")

    except ValueError:
        print("  Invalid input. Please enter a number.")
    except Exception as e:
        print(f"  Error: {e}")


def list_admins():
    """List all current admins"""
    players = Player.get_all(active_only=True)
    admins = [p for p in players if p.get('role', 'player') == 'admin']

    list_players(admins, "Current Admins")


def list_all_players():
    """List all players"""
    players = Player.get_all(active_only=True)
    list_players(players, "All Active Players")


def main():
    """Main function"""
    # Initialize data store
    init_data_store(Config.DATA_DIR)

    print("\nInitializing...")

    while True:
        display_menu()

        try:
            choice = input("Select an option (1-5): ").strip()

            if choice == '1':
                promote_to_admin()
            elif choice == '2':
                demote_to_player()
            elif choice == '3':
                list_admins()
            elif choice == '4':
                list_all_players()
            elif choice == '5':
                print("\nGoodbye!")
                sys.exit(0)
            else:
                print("\n  Invalid choice. Please select 1-5.")

        except KeyboardInterrupt:
            print("\n\nGoodbye!")
            sys.exit(0)
        except Exception as e:
            print(f"\n  Error: {e}")


if __name__ == '__main__':
    main()
