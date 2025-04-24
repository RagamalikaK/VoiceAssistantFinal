import os
import requests
import re
from typing import List, Dict, Optional
import logging
import json
from .llm_utils import get_llm_response

# Configure logging with more detailed format
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Add file handler for MBTA API logs
api_log_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs', 'mbta_api.log')
os.makedirs(os.path.dirname(api_log_file), exist_ok=True)
file_handler = logging.FileHandler(api_log_file)
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(file_handler)

# MBTA API base URL
MBTA_API_BASE_URL = "https://api-v3.mbta.com"

def extract_route_number(query: str) -> Optional[str]:
    """
    Extract route number from query string.
    
    Args:
        query: User's voice query
        
    Returns:
        Route number if found, None otherwise
    """
    # Look for patterns like "route 66", "66 bus", "#66", etc.
    patterns = [
        r'route\s+(\d+)',  # matches "route 66"
        r'(\d+)\s+bus',    # matches "66 bus"
        r'#(\d+)',         # matches "#66"
        r'number\s+(\d+)', # matches "number 66"
        r'(\d+)',          # matches just "66" - use last as it's most general
    ]
    
    for pattern in patterns:
        match = re.search(pattern, query.lower())
        if match:
            return match.group(1)
    return None

def get_routes(filter_params: Optional[Dict] = None) -> List[Dict]:
    """
    Get MBTA routes information.
    
    Args:
        filter_params (dict, optional): Dictionary of filter parameters for the API
            Examples:
            - type: List of route types (0=subway, 1=subway, 2=commuter rail, 3=bus, 4=ferry)
            - direction_id: 0 or 1 (inbound/outbound)
            - stop: Filter by stop
            
    Returns:
        List of dictionaries containing route information
    """
    try:
        # Construct the API URL
        url = f"{MBTA_API_BASE_URL}/routes"
        
        # Add API key if available
        headers = {}
        api_key = os.getenv("MBTA_API_KEY")
        if api_key:
            headers["x-api-key"] = api_key
            logger.info("Using MBTA API key for authentication")
        else:
            logger.warning("No MBTA API key found in environment variables")
            
        # Log API request details
        logger.info(f"Making request to MBTA API: GET {url}")
        if filter_params:
            logger.info(f"With filter parameters: {json.dumps(filter_params, indent=2)}")
            
        # Make the API request
        response = requests.get(url, headers=headers, params=filter_params)
        response.raise_for_status()
        
        # Parse and log the response
        data = response.json()
        routes_count = len(data.get("data", []))
        logger.info(f"Successfully retrieved {routes_count} routes from MBTA API")
        logger.debug(f"Full API response: {json.dumps(data, indent=2)}")
        
        return data.get("data", [])
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching MBTA routes: {str(e)}")
        if hasattr(e.response, 'text'):
            logger.error(f"API error response: {e.response.text}")
        return []

def format_route_response(routes: List[Dict], query: str) -> str:
    """
    Format route information into a natural language response using LLM.
    
    Args:
        routes: List of route dictionaries from the MBTA API
        query: Original user query to provide context-aware responses
        
    Returns:
        Formatted string response
    """
    logger.info(f"Formatting response for {len(routes)} routes")
    
    if not routes:
        logger.info("No routes found, returning default message")
        return "I couldn't find any routes matching your criteria. Would you like to try a different search?"

    # Prepare context for LLM
    route_data = []
    for route in routes:
        attributes = route.get("attributes", {})
        route_info = {
            "id": route.get("id"),
            "name": attributes.get("long_name"),
            "short_name": attributes.get("short_name"),
            "description": attributes.get("description"),
            "direction_names": attributes.get("direction_names", []),
            "direction_destinations": attributes.get("direction_destinations", []),
            "type": attributes.get("type")
        }
        route_data.append(route_info)

    # Create a system prompt for the LLM
    system_prompt = f"""You are an MBTA transit assistant helping users with route information. 
User Query: {query}

Here is the route data from the MBTA API:
{json.dumps(route_data, indent=2)}

Please analyze this data and provide a natural, conversational response that:
1. Directly answers the user's specific question about routes
2. Includes relevant details about origins, destinations, and service patterns
3. Uses a friendly, helpful tone
4. Keeps the response concise but informative
5. Mentions route numbers consistently (e.g., "Route 66" instead of just "66")
6. If the query is about a specific route's origin/destination, focus on that specific detail

Format your response in natural language as if you're having a conversation."""

    # Get LLM response
    try:
        response = get_llm_response(system_prompt, [])
        logger.info("Successfully generated LLM response")
        return response
    except Exception as e:
        logger.error(f"Error getting LLM response: {str(e)}")
        # Fall back to basic formatting if LLM fails
        return basic_format_response(routes, query)

def basic_format_response(routes: List[Dict], query: str) -> str:
    """
    Basic formatting fallback when LLM is unavailable.
    """
    route_number = extract_route_number(query)
    if route_number and len(routes) == 1:
        route = routes[0]
        attributes = route.get("attributes", {})
        name = attributes.get("long_name", "")
        description = attributes.get("description", "")
        
        if "origin" in query.lower() or "start" in query.lower() or "from" in query.lower():
            origin = name.split(" - ")[0] if " - " in name else name.split(" to ")[0]
            return f"Route {route_number} originates from {origin}."
        elif "destination" in query.lower() or "end" in query.lower() or "to" in query.lower():
            destination = name.split(" - ")[-1] if " - " in name else name.split(" to ")[-1]
            return f"Route {route_number} goes to {destination}."
        else:
            response = f"Route {route_number} runs from {name}."
            if description:
                response += f" {description}"
            return response
    
    response_parts = []
    for route in routes:
        attributes = route.get("attributes", {})
        name = attributes.get("long_name")
        short_name = attributes.get("short_name")
        description = attributes.get("description")
        
        route_info = f"The {short_name} {name}" if short_name else f"The {name}"
        if description:
            route_info += f" - {description}"
            
        response_parts.append(route_info)
    
    if len(response_parts) == 1:
        return response_parts[0]
    elif len(response_parts) == 2:
        return f"{response_parts[0]} and {response_parts[1]}"
    else:
        return ", ".join(response_parts[:-1]) + f", and {response_parts[-1]}"

def get_route_suggestions(query: str) -> str:
    """
    Get route suggestions based on user query.
    
    Args:
        query: User's voice query
        
    Returns:
        Natural language response with route suggestions
    """
    logger.info(f"Processing route suggestion query: '{query}'")
    
    # Extract route number if present
    route_number = extract_route_number(query)
    filter_params = {}
    
    if route_number:
        # If a specific route number is mentioned, filter by route ID
        logger.info(f"Detected specific route number: {route_number}")
        filter_params["filter[id]"] = route_number
    
    # Check for transit type keywords
    if any(word in query.lower() for word in ["subway", "train", "rail", "line"]):
        filter_params["type"] = "0,1"  # Subway/Light Rail
        logger.info("Detected query for subway/light rail routes")
    elif "bus" in query.lower():
        filter_params["type"] = "3"  # Bus
        logger.info("Detected query for bus routes")
    elif "ferry" in query.lower():
        filter_params["type"] = "4"  # Ferry
        logger.info("Detected query for ferry routes")
    elif "commuter" in query.lower():
        filter_params["type"] = "2"  # Commuter Rail
        logger.info("Detected query for commuter rail routes")
    else:
        logger.info("No specific route type detected, querying all routes")
    
    # Get routes from MBTA API
    routes = get_routes(filter_params)
    
    # Format and return the response
    response = format_route_response(routes, query)
    logger.info("Route suggestion response generated successfully")
    return response 