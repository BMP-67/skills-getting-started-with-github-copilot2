"""
Integration tests for the Mergington High School Activities API.
Tests more complex scenarios and edge cases.
"""
import pytest
from fastapi.testclient import TestClient


class TestActivityManagement:
    """Integration tests for activity management workflows."""
    
    def test_complete_student_journey(self, client, reset_activities):
        """Test a complete student journey through multiple activities."""
        student_email = "journey_student@mergington.edu"
        
        # Student signs up for multiple activities
        activities_to_join = ["Chess Club", "Programming Class", "Art Workshop"]
        
        for activity in activities_to_join:
            response = client.post(f"/activities/{activity}/signup?email={student_email}")
            assert response.status_code == 200
        
        # Verify student is in all activities
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        
        for activity in activities_to_join:
            assert student_email in activities_data[activity]["participants"]
        
        # Student leaves one activity
        leave_activity = "Chess Club"
        response = client.delete(f"/activities/{leave_activity}/unregister?email={student_email}")
        assert response.status_code == 200
        
        # Verify student is removed from that activity but still in others
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        
        assert student_email not in activities_data[leave_activity]["participants"]
        for activity in activities_to_join:
            if activity != leave_activity:
                assert student_email in activities_data[activity]["participants"]
    
    def test_activity_capacity_tracking(self, client, reset_activities):
        """Test that activity capacity is tracked correctly."""
        activity_name = "Mathletes"  # Has max 10 participants
        
        # Get initial state
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        initial_count = len(activities_data[activity_name]["participants"])
        max_participants = activities_data[activity_name]["max_participants"]
        
        # Calculate how many more can join
        available_spots = max_participants - initial_count
        
        # Add students up to the calculated available spots
        new_students = []
        for i in range(min(available_spots, 5)):  # Add up to 5 or available spots, whichever is smaller
            email = f"capacity_test_{i}@mergington.edu"
            new_students.append(email)
            response = client.post(f"/activities/{activity_name}/signup?email={email}")
            assert response.status_code == 200
        
        # Verify all were added
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        current_participants = activities_data[activity_name]["participants"]
        
        for email in new_students:
            assert email in current_participants
        
        assert len(current_participants) == initial_count + len(new_students)
    
    def test_concurrent_signups_same_activity(self, client, reset_activities):
        """Test multiple students signing up for the same activity."""
        activity_name = "Basketball Club"
        students = [
            "concurrent1@mergington.edu",
            "concurrent2@mergington.edu", 
            "concurrent3@mergington.edu",
            "concurrent4@mergington.edu"
        ]
        
        # Get initial participant count
        initial_response = client.get("/activities")
        initial_count = len(initial_response.json()[activity_name]["participants"])
        
        # Sign up all students
        for student in students:
            response = client.post(f"/activities/{activity_name}/signup?email={student}")
            assert response.status_code == 200
        
        # Verify all are registered
        final_response = client.get("/activities")
        final_participants = final_response.json()[activity_name]["participants"]
        
        for student in students:
            assert student in final_participants
        
        assert len(final_participants) == initial_count + len(students)


class TestErrorHandling:
    """Test error handling and edge cases."""
    
    def test_malformed_activity_names(self, client, reset_activities):
        """Test handling of malformed activity names."""
        malformed_names = [
            "Activity%20With%20Encoding",
            "Activity/With/Slashes",
            "Activity With Spaces",
            ""
        ]
        
        for name in malformed_names:
            # Most should return 404 for non-existent activities
            signup_response = client.post(f"/activities/{name}/signup?email=test@mergington.edu")
            unregister_response = client.delete(f"/activities/{name}/unregister?email=test@mergington.edu")
            
            # Either 404 (not found) or other appropriate error codes
            assert signup_response.status_code in [404, 422, 400]
            assert unregister_response.status_code in [404, 422, 400]
    
    def test_malformed_emails(self, client, reset_activities):
        """Test handling of various email formats."""
        emails = [
            "valid@mergington.edu",
            "another.valid+email@mergington.edu",
            "invalid-email",
            "",
            "no@domain",
            "@nodomain.com",
            "space @domain.com"
        ]
        
        activity_name = "Chess Club"
        
        for email in emails:
            signup_response = client.post(f"/activities/{activity_name}/signup?email={email}")
            # The API should handle all emails as strings, but some might be invalid for business logic
            assert signup_response.status_code in [200, 400, 422]
    
    def test_special_characters_in_emails(self, client, reset_activities):
        """Test emails with special characters that need URL encoding."""
        # Note: These are valid email formats that might need special handling
        special_emails = [
            "user.name@mergington.edu",
            "user_name@mergington.edu"
        ]
        
        activity_name = "Programming Class"
        
        for email in special_emails:
            # Test signup
            signup_response = client.post(f"/activities/{activity_name}/signup?email={email}")
            assert signup_response.status_code == 200
            
            # Verify registration
            activities_response = client.get("/activities")
            activities_data = activities_response.json()
            assert email in activities_data[activity_name]["participants"]
            
            # Test unregister
            unregister_response = client.delete(f"/activities/{activity_name}/unregister?email={email}")
            assert unregister_response.status_code == 200
            
            # Verify unregistration
            activities_response = client.get("/activities")
            activities_data = activities_response.json()
            assert email not in activities_data[activity_name]["participants"]
    
    def test_plus_sign_in_email(self, client, reset_activities):
        """Test email with plus sign that needs special URL encoding."""
        import urllib.parse
        
        activity_name = "Science Club"
        email = "user+tag@mergington.edu"
        encoded_email = urllib.parse.quote_plus(email)
        
        # Test signup with properly encoded email
        signup_response = client.post(f"/activities/{activity_name}/signup?email={encoded_email}")
        assert signup_response.status_code == 200
        
        # Verify registration
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert email in activities_data[activity_name]["participants"]
        
        # Test unregister with properly encoded email
        unregister_response = client.delete(f"/activities/{activity_name}/unregister?email={encoded_email}")
        assert unregister_response.status_code == 200
        
        # Verify unregistration
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert email not in activities_data[activity_name]["participants"]


class TestAPIConsistency:
    """Test API consistency and behavior."""
    
    def test_response_format_consistency(self, client, reset_activities):
        """Test that all endpoints return consistent response formats."""
        # Test activities endpoint
        activities_response = client.get("/activities")
        assert activities_response.status_code == 200
        assert "application/json" in activities_response.headers.get("content-type", "")
        
        # Test signup endpoint
        signup_response = client.post("/activities/Chess Club/signup?email=test@mergington.edu")
        assert signup_response.status_code == 200
        signup_data = signup_response.json()
        assert "message" in signup_data
        assert isinstance(signup_data["message"], str)
        
        # Test unregister endpoint
        unregister_response = client.delete("/activities/Chess Club/unregister?email=test@mergington.edu")
        assert unregister_response.status_code == 200
        unregister_data = unregister_response.json()
        assert "message" in unregister_data
        assert isinstance(unregister_data["message"], str)
    
    def test_error_response_format_consistency(self, client, reset_activities):
        """Test that error responses have consistent format."""
        # Test 404 error
        response_404 = client.post("/activities/NonExistent/signup?email=test@mergington.edu")
        assert response_404.status_code == 404
        error_data = response_404.json()
        assert "detail" in error_data
        
        # Test 400 error (duplicate signup)
        # First signup
        client.post("/activities/Chess Club/signup?email=duplicate@mergington.edu")
        # Duplicate signup
        response_400 = client.post("/activities/Chess Club/signup?email=duplicate@mergington.edu")
        assert response_400.status_code == 400
        error_data = response_400.json()
        assert "detail" in error_data
    
    def test_activity_data_structure_consistency(self, client, reset_activities):
        """Test that all activities have consistent data structure."""
        response = client.get("/activities")
        activities = response.json()
        
        required_fields = ["description", "schedule", "max_participants", "participants"]
        
        for activity_name, activity_data in activities.items():
            assert isinstance(activity_name, str)
            assert len(activity_name) > 0
            
            for field in required_fields:
                assert field in activity_data, f"Missing field {field} in activity {activity_name}"
            
            # Test field types
            assert isinstance(activity_data["description"], str)
            assert isinstance(activity_data["schedule"], str)
            assert isinstance(activity_data["max_participants"], int)
            assert isinstance(activity_data["participants"], list)
            
            # Test that all participants are strings (emails)
            for participant in activity_data["participants"]:
                assert isinstance(participant, str)