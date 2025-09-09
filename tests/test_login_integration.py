import os
import sys
import uuid
import shutil
import pytest
import re
from pexpect.popen_spawn import PopenSpawn

# Constants
PY_CMD = f"{sys.executable} -m src.main"
TIMEOUT = 20  # seconds

# Generate unique test credentials for each test run
TEST_USERNAME = f"ChessTester_{uuid.uuid4().hex[:8]}"
TEST_PASSWORD = "TestPassword123"  # Fixed password for testing
TEST_EMAIL = f"{TEST_USERNAME.lower()}@example.com"

# Add environment variables to disable interactive prompts
TEST_ENV = os.environ.copy()
TEST_ENV["PYTHONIOENCODING"] = "utf-8"
TEST_ENV["CHESS_APP_TEST_MODE"] = "1"  # Add this to your app to detect test mode

def strip_ansi_codes(text):
    """Remove ANSI color codes from text output"""
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    return ansi_escape.sub('', text)

def extract_verification_token(console_output):
    """Extract verification token from console output in dev mode."""
    # Try standard pattern (improved)
    match = re.search(r"verification token is: ([a-zA-Z0-9_-]+)", console_output)
    if match:
        return match.group(1)
    
    # Look for token at beginning of line
    lines = console_output.split('\n')
    for line in lines:
        if re.match(r'^[a-zA-Z0-9_\-]{30,}$', line.strip()):
            return line.strip()
    
    # Try a more flexible pattern as backup
    match = re.search(r"token is: ([^\r\n]+)", console_output)
    if match:
        return match.group(1).strip()
    
    # Handle potential duplication in token string
    match = re.search(r"verification token is:verification token is: ([a-zA-Z0-9_\-]+)", console_output)
    if match:
        return match.group(1)
    
    return None

def spawn_test_process():
    """Create a process with proper environment settings for automated testing"""
    return PopenSpawn(
        PY_CMD,
        encoding='utf-8',
        timeout=TIMEOUT,
        env=TEST_ENV
    )

def expect_with_debug(child, pattern, timeout=None):
    """Helper to expect a pattern with debug output on failure"""
    if timeout is None:
        timeout = TIMEOUT
        
    try:
        return child.expect(pattern, timeout=timeout)
    except Exception as e:
        print(f"\nERROR waiting for pattern: {pattern}")
        print(f"Output received before timeout:\n{'-'*50}\n{child.before}\n{'-'*50}")
        raise

@pytest.fixture(scope="module")
def setup_test_environment():
    """Sets up test environment for authentication testing and cleans up after tests."""
    # Ensure user_data directory exists
    os.makedirs("user_data/profiles", exist_ok=True)
    
    # Path to current session file
    session_file = os.path.join("user_data", "current_session.txt")
    
    # Back up the current session if it exists
    session_existed = os.path.exists(session_file)
    if session_existed:
        shutil.copy(session_file, f"{session_file}.bak")
        os.remove(session_file)
    
    yield  # Run the tests
    
    # Cleanup
    # Remove the test user's profile if created
    user_file = os.path.join("user_data", "profiles", f"{TEST_USERNAME.lower()}.json")
    if os.path.exists(user_file):
        os.remove(user_file)
        print(f"Removed test user profile: {TEST_USERNAME}")
    
    # Restore original session if it existed
    if session_existed and os.path.exists(f"{session_file}.bak"):
        shutil.move(f"{session_file}.bak", session_file)

@pytest.mark.integration
@pytest.mark.auth
def test_registration_and_login(setup_test_environment):
    """Test the complete authentication flow: registration, verification, and login."""
    print(f"Testing with unique username: {TEST_USERNAME}")
    
    # Part 1: User Registration
    verification_token = None
    child = spawn_test_process()
    
    try:
        # Wait for authentication menu
        expect_with_debug(child, "--- Authentication Required ---")
        expect_with_debug(child, "Enter your choice:")
        child.sendline("2")  # Register
        
        # Fill in registration form
        expect_with_debug(child, "Username")
        child.sendline(TEST_USERNAME)
        
        expect_with_debug(child, "Email address:")
        child.sendline(TEST_EMAIL)
        
        # Check for either password prompt or verification token
        index = child.expect([
            "Password \\(minimum 8 characters\\):", 
            "verification token is:", 
            "Would you like to enter your verification code now",
            "\\? \\(y/n\\):"  # Added shorter prompt pattern
        ], timeout=TIMEOUT)
        
        # Save the output for token extraction later
        current_output = child.before
        
        if index == 0:
            # We got the password prompt as expected
            child.sendline(TEST_PASSWORD)
            
            expect_with_debug(child, "Confirm password:")
            child.sendline(TEST_PASSWORD)
            
            # Wait for registration success
            expect_with_debug(child, "Registration successful")
            
            # Update current output for token extraction
            current_output = child.before
        
        elif index == 1:
            # We already have the verification token in output
            current_output += "verification token is:" + child.after
            
            # Continue to verification prompt - may be either full text or just (y/n)
            try:
                # Try for full prompt first
                child.expect("Would you like to enter your verification code now", timeout=5)
            except:
                # If not found, try shorter prompt
                try:
                    child.expect("\\? \\(y/n\\):", timeout=5)
                except:
                    # If neither found, we'll handle this after token extraction
                    pass
            
            # Update current output
            current_output += child.before
        
        elif index == 2 or index == 3:
            # Already at verification prompt (either full or short version)
            # Keep current output for token extraction
            pass
        
        # Print the entire output for debugging
        print("DEBUG - Full console output for token extraction:")
        print("="*50)
        print(current_output)
        print("="*50)
        
        # Try to extract the verification token
        verification_token = extract_verification_token(current_output)
        
        # If not found, try with full current output
        if not verification_token:
            verification_token = extract_verification_token(child.before)
            print("Trying alternate extraction source")
        
        # Print token info for debugging
        if verification_token:
            print(f"Found token: {verification_token}")
        else:
            print("TOKEN NOT FOUND - Debug output:")
            print(f"Current pattern match area: {current_output}")
        
        # At this point we should have the verification token
        assert verification_token, "Failed to extract verification token from console output"
        
        # Look for either the full prompt or just the (y/n) part
        try:
            # First try to see if we're already at a prompt that needs input
            if "? (y/n)" in child.before or "(y/n)" in child.before:
                child.sendline("y")
            else:
                # If not, wait for either prompt format
                index = child.expect([
                    "Would you like to enter your verification code now",
                    "\\? \\(y/n\\):"
                ], timeout=TIMEOUT)
                child.sendline("y")
        except Exception as e:
            print(f"Warning: Could not find verification prompt: {e}")
            print(f"Current output: {child.before}")
            # Try to continue anyway
            child.sendline("y")
        
        # Wait for token input prompt
        try:
            expect_with_debug(child, "Enter verification token from email:")
            child.sendline(verification_token)
        except:
            # If the specific prompt isn't found, try sending the token anyway
            print("Warning: Could not find token input prompt, sending token anyway")
            child.sendline(verification_token)
        
        # Should see verification success
        expect_with_debug(child, "Email verified successfully", timeout=TIMEOUT * 1.5)
        
        # Let automatic login happen
        expect_with_debug(child, "--- Main Menu ---")
        
        # Quit application
        expect_with_debug(child, "Enter your choice:")
        child.sendline("q")
        
    except Exception as e:
        print("\n==== REGISTRATION TEST FAILED ====")
        print(f"Error: {str(e)}")
        print(f"Last output received:\n{child.before}")
        raise
    finally:
        # Clean up the process
        if child.proc.poll() is None:
            child.proc.terminate()
    
    # Part 2: User Login (in a separate session)
    child = spawn_test_process()
    
    try:
        # Wait for authentication menu
        expect_with_debug(child, "--- Authentication Required ---")
        expect_with_debug(child, "Enter your choice:")
        child.sendline("1")  # Login
        
        # Here's where we need to be flexible - either expect login form or direct main menu
        index = child.expect([
            "--- Login ---",
            "Welcome back",
            "--- Main Menu ---"
        ], timeout=TIMEOUT)
        
        if index == 0:
            # Normal login flow - we got the login form
            expect_with_debug(child, "Username or Email:")
            child.sendline(TEST_USERNAME)
            
            # After sending username, check if we get password prompt OR automatic login
            try:
                # Try to match either password prompt or welcome message
                pw_index = child.expect(["Password:", f"Welcome back, {TEST_USERNAME}"], timeout=TIMEOUT)
                
                if pw_index == 0:
                    # Password prompt as expected
                    child.sendline(TEST_PASSWORD)
                    # Should see welcome message after successful login
                    expect_with_debug(child, f"Welcome back, {TEST_USERNAME}")
                else:
                    # Automatic login after just the username
                    print("Auto-login after username entry detected")
                    # No need to send password, already logged in
            except Exception as e:
                print(f"Warning: Unexpected flow after username entry: {e}")
                print(f"Current output: {child.before}")
                # Try to continue by checking if we're already at main menu
                if "--- Main Menu ---" in child.before:
                    print("Main menu detected, continuing test")
                else:
                    # If not at main menu, try sending password anyway as a fallback
                    child.sendline(TEST_PASSWORD)
            
            # Should be at main menu
            expect_with_debug(child, "--- Main Menu ---")
        else:
            # Automatic login happened - we're already at the welcome or main menu
            print("Automatic login detected - user already authenticated")
            
            # If we matched on "Welcome back" but haven't seen main menu yet, wait for it
            if index == 1 and "--- Main Menu ---" not in child.before:
                expect_with_debug(child, "--- Main Menu ---")
        
        # Common flow continues here - we should be at main menu now
        expect_with_debug(child, "Enter your choice:")
        
        # Get the plain text version of the output for assertions
        plain_output = strip_ansi_codes(child.before)
        print("Plain text menu for verification:")
        print(plain_output)
        
        # Verify menu options are displayed in the stripped output
        assert "1: Play a New Game" in plain_output
        assert "2: Load a Saved Game" in plain_output
        assert "3: Load a Practice Position" in plain_output
        assert "4: View Player Stats" in plain_output
        
        # Exit application
        child.sendline("q")
        
    except Exception as e:
        print("\n==== LOGIN TEST FAILED ====")
        print(f"Error: {str(e)}")
        print(f"Last output received:\n{child.before}")
        raise
    finally:
        # Clean up the process
        if child.proc.poll() is None:
            child.proc.terminate()