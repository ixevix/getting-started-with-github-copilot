"""
FastAPI tests for Mergington High School Activities API

Uses AAA (Arrange-Act-Assert) pattern for clear test structure.
"""

import pytest
from fastapi.testclient import TestClient
from copy import deepcopy
from src.app import app, activities


@pytest.fixture
def client():
    """
    Fixture: Create a fresh TestClient with isolated activities state.
    This ensures each test starts with clean data.
    """
    # Arrange: Save original activities
    original_activities = deepcopy(activities)
    
    # Create client
    test_client = TestClient(app)
    
    yield test_client
    
    # Cleanup: Restore original state after test
    activities.clear()
    activities.update(original_activities)


class TestGetActivities:
    """Tests for GET /activities endpoint"""

    def test_get_activities_returns_all_activities(self, client):
        """Arrange-Act-Assert: Fetch activities and verify structure"""
        # Arrange
        expected_keys = {"Chess Club", "Programming Class", "Gym Class"}

        # Act
        response = client.get("/activities")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert set(data.keys()) >= expected_keys
        for activity in data.values():
            assert "description" in activity
            assert "schedule" in activity
            assert "max_participants" in activity
            assert "participants" in activity
            assert isinstance(activity["participants"], list)

    def test_get_activities_includes_participant_list(self, client):
        """Arrange-Act-Assert: Verify participant lists are included"""
        # Arrange
        # (Activities already have participants from the initial data)

        # Act
        response = client.get("/activities")

        # Assert
        data = response.json()
        chess = data.get("Chess Club")
        assert chess is not None
        assert len(chess["participants"]) > 0
        assert "michael@mergington.edu" in chess["participants"]


class TestSignupForActivity:
    """Tests for POST /activities/{activity_name}/signup endpoint"""

    def test_signup_success(self, client):
        """Arrange-Act-Assert: Successfully sign up a new student"""
        # Arrange
        activity_name = "Chess Club"
        email = "newstudent@mergington.edu"

        # Act
        response = client.post(
            f"/activities/{activity_name}/signup",
            params={"email": email}
        )

        # Assert
        assert response.status_code == 200
        assert "Signed up" in response.json()["message"]
        
        # Verify participant was added
        activities_list = client.get("/activities").json()
        assert email in activities_list[activity_name]["participants"]

    def test_signup_duplicate_student_fails(self, client):
        """Arrange-Act-Assert: Prevent duplicate signup for same student"""
        # Arrange
        activity_name = "Chess Club"
        email = "michael@mergington.edu"  # Already signed up

        # Act
        response = client.post(
            f"/activities/{activity_name}/signup",
            params={"email": email}
        )

        # Assert
        assert response.status_code == 400
        assert "already signed up" in response.json()["detail"].lower()

    def test_signup_nonexistent_activity_fails(self, client):
        """Arrange-Act-Assert: Prevent signup to non-existent activity"""
        # Arrange
        activity_name = "Nonexistent Activity"
        email = "student@mergington.edu"

        # Act
        response = client.post(
            f"/activities/{activity_name}/signup",
            params={"email": email}
        )

        # Assert
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_signup_to_full_activity_fails(self, client):
        """Arrange-Act-Assert: Prevent signup when activity is at max capacity"""
        # Arrange
        activity_name = "Tennis Club"
        activities[activity_name]["max_participants"] = 1  # Set to 1
        activities[activity_name]["participants"] = ["existing@mergington.edu"]  # Already full
        new_email = "newstudent@mergington.edu"

        # Act
        response = client.post(
            f"/activities/{activity_name}/signup",
            params={"email": new_email}
        )

        # Assert
        assert response.status_code == 400
        assert "full" in response.json()["detail"].lower()

    def test_signup_updates_participant_count(self, client):
        """Arrange-Act-Assert: Verify participant count increases after signup"""
        # Arrange
        activity_name = "Programming Class"
        email = "alice@mergington.edu"
        initial_response = client.get("/activities")
        initial_count = len(initial_response.json()[activity_name]["participants"])

        # Act
        client.post(f"/activities/{activity_name}/signup", params={"email": email})

        # Assert
        updated_response = client.get("/activities")
        updated_count = len(updated_response.json()[activity_name]["participants"])
        assert updated_count == initial_count + 1


class TestUnregisterForActivity:
    """Tests for DELETE /activities/{activity_name}/signup endpoint"""

    def test_unregister_success(self, client):
        """Arrange-Act-Assert: Successfully unregister a student"""
        # Arrange
        activity_name = "Chess Club"
        email = "michael@mergington.edu"  # Exists in Chess Club

        # Act
        response = client.delete(
            f"/activities/{activity_name}/signup",
            params={"email": email}
        )

        # Assert
        assert response.status_code == 200
        assert "Unregistered" in response.json()["message"]
        
        # Verify participant was removed
        activities_list = client.get("/activities").json()
        assert email not in activities_list[activity_name]["participants"]

    def test_unregister_nonexistent_student_fails(self, client):
        """Arrange-Act-Assert: Prevent unregistering non-existent student"""
        # Arrange
        activity_name = "Chess Club"
        email = "nonexistent@mergington.edu"

        # Act
        response = client.delete(
            f"/activities/{activity_name}/signup",
            params={"email": email}
        )

        # Assert
        assert response.status_code == 400
        assert "not registered" in response.json()["detail"].lower()

    def test_unregister_nonexistent_activity_fails(self, client):
        """Arrange-Act-Assert: Prevent unregistering from non-existent activity"""
        # Arrange
        activity_name = "Nonexistent Activity"
        email = "student@mergington.edu"

        # Act
        response = client.delete(
            f"/activities/{activity_name}/signup",
            params={"email": email}
        )

        # Assert
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_unregister_updates_participant_count(self, client):
        """Arrange-Act-Assert: Verify participant count decreases after unregister"""
        # Arrange
        activity_name = "Chess Club"
        email = "michael@mergington.edu"
        initial_response = client.get("/activities")
        initial_count = len(initial_response.json()[activity_name]["participants"])

        # Act
        client.delete(f"/activities/{activity_name}/signup", params={"email": email})

        # Assert
        updated_response = client.get("/activities")
        updated_count = len(updated_response.json()[activity_name]["participants"])
        assert updated_count == initial_count - 1


class TestIntegration:
    """Integration tests combining multiple operations"""

    def test_signup_and_unregister_workflow(self, client):
        """Arrange-Act-Assert: Complete signup and unregister workflow"""
        # Arrange
        activity_name = "Drama Club"
        email = "bob@mergington.edu"

        # Act 1: Sign up
        signup_response = client.post(
            f"/activities/{activity_name}/signup",
            params={"email": email}
        )

        # Assert 1
        assert signup_response.status_code == 200

        # Act 2: Verify participant is in list
        get_response = client.get("/activities")
        assert email in get_response.json()[activity_name]["participants"]

        # Act 3: Unregister
        unregister_response = client.delete(
            f"/activities/{activity_name}/signup",
            params={"email": email}
        )

        # Assert 3
        assert unregister_response.status_code == 200

        # Act 4: Verify participant is removed
        final_response = client.get("/activities")
        assert email not in final_response.json()[activity_name]["participants"]

    def test_multiple_signups_to_same_activity(self, client):
        """Arrange-Act-Assert: Multiple different students can sign up"""
        # Arrange
        activity_name = "Science Club"
        emails = ["student1@mergington.edu", "student2@mergington.edu", "student3@mergington.edu"]

        # Act
        for email in emails:
            response = client.post(
                f"/activities/{activity_name}/signup",
                params={"email": email}
            )
            assert response.status_code == 200

        # Assert
        final_response = client.get("/activities")
        participants = final_response.json()[activity_name]["participants"]
        for email in emails:
            assert email in participants
