"""
Test suite for the Mergington High School Activities API.
"""
import pytest
from fastapi.testclient import TestClient


class TestRootEndpoint:
    """Test cases for the root endpoint."""
    
    def test_root_redirect(self, client):
        """Test that root endpoint redirects to static index.html."""
        response = client.get("/", follow_redirects=False)
        assert response.status_code == 307  # Temporary redirect
        assert "/static/index.html" in response.headers["location"]


class TestActivitiesEndpoint:
    """Test cases for the activities endpoint."""
    
    def test_get_activities_success(self, client, reset_activities):
        """Test successful retrieval of activities."""
        response = client.get("/activities")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, dict)
        
        # Check that we have some activities
        assert len(data) > 0
        
        # Check structure of first activity
        first_activity = list(data.values())[0]
        assert "description" in first_activity
        assert "schedule" in first_activity
        assert "max_participants" in first_activity
        assert "participants" in first_activity
        assert isinstance(first_activity["participants"], list)
        assert isinstance(first_activity["max_participants"], int)
    
    def test_get_activities_content(self, client, reset_activities):
        """Test that activities contain expected content."""
        response = client.get("/activities")
        data = response.json()
        
        # Check for some expected activities
        assert "Chess Club" in data
        assert "Programming Class" in data
        
        # Verify Chess Club details
        chess_club = data["Chess Club"]
        assert "chess tournaments" in chess_club["description"].lower()
        assert chess_club["max_participants"] == 12


class TestSignupEndpoint:
    """Test cases for the signup endpoint."""
    
    def test_signup_success(self, client, reset_activities):
        """Test successful signup for an activity."""
        activity_name = "Chess Club"
        email = "newstudent@mergington.edu"
        
        response = client.post(f"/activities/{activity_name}/signup?email={email}")
        assert response.status_code == 200
        
        data = response.json()
        assert "message" in data
        assert email in data["message"]
        assert activity_name in data["message"]
        
        # Verify the student was actually added
        activities_response = client.get("/activities")
        activities = activities_response.json()
        assert email in activities[activity_name]["participants"]
    
    def test_signup_nonexistent_activity(self, client, reset_activities):
        """Test signup for a non-existent activity."""
        response = client.post("/activities/Nonexistent Club/signup?email=test@mergington.edu")
        assert response.status_code == 404
        
        data = response.json()
        assert data["detail"] == "Activity not found"
    
    def test_signup_duplicate_registration(self, client, reset_activities):
        """Test that duplicate registration is prevented."""
        activity_name = "Chess Club"
        email = "michael@mergington.edu"  # Already registered in Chess Club
        
        response = client.post(f"/activities/{activity_name}/signup?email={email}")
        assert response.status_code == 400
        
        data = response.json()
        assert "already signed up" in data["detail"].lower()
    
    def test_signup_multiple_students_same_activity(self, client, reset_activities):
        """Test multiple students can sign up for the same activity."""
        activity_name = "Programming Class"
        emails = ["student1@mergington.edu", "student2@mergington.edu", "student3@mergington.edu"]
        
        for email in emails:
            response = client.post(f"/activities/{activity_name}/signup?email={email}")
            assert response.status_code == 200
        
        # Verify all students were added
        activities_response = client.get("/activities")
        activities = activities_response.json()
        for email in emails:
            assert email in activities[activity_name]["participants"]
    
    def test_signup_with_special_characters_in_activity_name(self, client, reset_activities):
        """Test signup works with URL encoding for activity names."""
        # Test with spaces (should be URL encoded)
        response = client.post("/activities/Chess%20Club/signup?email=test@mergington.edu")
        assert response.status_code == 200


class TestUnregisterEndpoint:
    """Test cases for the unregister endpoint."""
    
    def test_unregister_success(self, client, reset_activities):
        """Test successful unregistration from an activity."""
        activity_name = "Chess Club"
        email = "michael@mergington.edu"  # Already registered
        
        response = client.delete(f"/activities/{activity_name}/unregister?email={email}")
        assert response.status_code == 200
        
        data = response.json()
        assert "message" in data
        assert email in data["message"]
        assert activity_name in data["message"]
        
        # Verify the student was actually removed
        activities_response = client.get("/activities")
        activities = activities_response.json()
        assert email not in activities[activity_name]["participants"]
    
    def test_unregister_nonexistent_activity(self, client, reset_activities):
        """Test unregister from a non-existent activity."""
        response = client.delete("/activities/Nonexistent Club/unregister?email=test@mergington.edu")
        assert response.status_code == 404
        
        data = response.json()
        assert data["detail"] == "Activity not found"
    
    def test_unregister_student_not_registered(self, client, reset_activities):
        """Test unregister when student is not registered."""
        activity_name = "Chess Club"
        email = "notregistered@mergington.edu"
        
        response = client.delete(f"/activities/{activity_name}/unregister?email={email}")
        assert response.status_code == 400
        
        data = response.json()
        assert "not registered" in data["detail"].lower()
    
    def test_register_then_unregister(self, client, reset_activities):
        """Test complete workflow: register then unregister."""
        activity_name = "Science Club"
        email = "workflow_test@mergington.edu"
        
        # First, register
        signup_response = client.post(f"/activities/{activity_name}/signup?email={email}")
        assert signup_response.status_code == 200
        
        # Verify registration
        activities_response = client.get("/activities")
        activities = activities_response.json()
        assert email in activities[activity_name]["participants"]
        
        # Then, unregister
        unregister_response = client.delete(f"/activities/{activity_name}/unregister?email={email}")
        assert unregister_response.status_code == 200
        
        # Verify unregistration
        activities_response = client.get("/activities")
        activities = activities_response.json()
        assert email not in activities[activity_name]["participants"]


class TestActivityCapacity:
    """Test cases for activity capacity limits."""
    
    def test_activity_has_capacity_info(self, client, reset_activities):
        """Test that activities include capacity information."""
        response = client.get("/activities")
        activities = response.json()
        
        for activity_name, activity_info in activities.items():
            assert "max_participants" in activity_info
            assert "participants" in activity_info
            assert isinstance(activity_info["max_participants"], int)
            assert isinstance(activity_info["participants"], list)
            
            # Check that current participants don't exceed max
            current_count = len(activity_info["participants"])
            max_count = activity_info["max_participants"]
            assert current_count <= max_count


class TestEmailValidation:
    """Test cases for email parameter handling."""
    
    def test_signup_missing_email(self, client, reset_activities):
        """Test signup without email parameter."""
        response = client.post("/activities/Chess Club/signup")
        assert response.status_code == 422  # Unprocessable Entity
    
    def test_unregister_missing_email(self, client, reset_activities):
        """Test unregister without email parameter."""
        response = client.delete("/activities/Chess Club/unregister")
        assert response.status_code == 422  # Unprocessable Entity


class TestDataIntegrity:
    """Test cases for data integrity and persistence."""
    
    def test_multiple_operations_maintain_integrity(self, client, reset_activities):
        """Test that multiple operations maintain data integrity."""
        activity_name = "Drama Club"
        
        # Get initial state
        initial_response = client.get("/activities")
        initial_participants = initial_response.json()[activity_name]["participants"].copy()
        
        # Add a student
        new_email = "integrity_test@mergington.edu"
        signup_response = client.post(f"/activities/{activity_name}/signup?email={new_email}")
        assert signup_response.status_code == 200
        
        # Verify addition
        after_signup_response = client.get("/activities")
        after_signup_participants = after_signup_response.json()[activity_name]["participants"]
        assert new_email in after_signup_participants
        assert len(after_signup_participants) == len(initial_participants) + 1
        
        # Remove the student
        unregister_response = client.delete(f"/activities/{activity_name}/unregister?email={new_email}")
        assert unregister_response.status_code == 200
        
        # Verify removal - should be back to initial state
        final_response = client.get("/activities")
        final_participants = final_response.json()[activity_name]["participants"]
        assert set(final_participants) == set(initial_participants)