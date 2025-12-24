"""
External Knowledge Search Module
Searches GitHub, StackOverflow, and Dev.to for pattern-specific solutions
"""

import requests
from typing import List, Dict, Optional
from bs4 import BeautifulSoup
import urllib.parse


def search_github_repos(query: str, max_results: int = 5) -> List[Dict[str, str]]:
    """
    Search GitHub for repositories related to the pattern.
    
    Args:
        query: Search query (pattern-based)
        max_results: Maximum number of results to return
    
    Returns:
        List of dicts with {name, url, description, stars}
    """
    try:
        # Use GitHub Search API
        encoded_query = urllib.parse.quote(query)
        api_url = f"https://api.github.com/search/repositories?q={encoded_query}&sort=stars&order=desc&per_page={max_results}"
        
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "FYP-Code-Assistant"
        }
        
        response = requests.get(api_url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            repos = []
            
            for item in data.get("items", [])[:max_results]:
                repos.append({
                    "name": item.get("full_name", ""),
                    "url": item.get("html_url", ""),
                    "description": item.get("description", "No description available"),
                    "stars": item.get("stargazers_count", 0),
                    "language": item.get("language", "Unknown")
                })
            
            return repos
        else:
            print(f"GitHub API error: {response.status_code}")
            return []
            
    except Exception as e:
        print(f"GitHub search error: {e}")
        return []


def search_stackoverflow(query: str, max_results: int = 5) -> List[Dict[str, str]]:
    """
    Search StackOverflow for relevant threads.
    
    Args:
        query: Search query (pattern-based)
        max_results: Maximum number of results
    
    Returns:
        List of dicts with {title, url, score, answer_count}
    """
    try:
        # Use StackExchange API
        encoded_query = urllib.parse.quote(query)
        api_url = f"https://api.stackexchange.com/2.3/search/advanced?order=desc&sort=votes&q={encoded_query}&site=stackoverflow&pagesize={max_results}"
        
        response = requests.get(api_url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            questions = []
            
            for item in data.get("items", [])[:max_results]:
                questions.append({
                    "title": item.get("title", ""),
                    "url": item.get("link", ""),
                    "score": item.get("score", 0),
                    "answer_count": item.get("answer_count", 0),
                    "is_answered": item.get("is_answered", False)
                })
            
            return questions
        else:
            print(f"StackOverflow API error: {response.status_code}")
            return []
            
    except Exception as e:
        print(f"StackOverflow search error: {e}")
        return []


def search_dev_articles(query: str, max_results: int = 3) -> List[Dict[str, str]]:
    """
    Search Dev.to for articles related to the pattern.
    
    Args:
        query: Search query (pattern-based)
        max_results: Maximum number of results
    
    Returns:
        List of dicts with {title, url, author}
    """
    try:
        # Use Dev.to API
        encoded_query = urllib.parse.quote(query)
        api_url = f"https://dev.to/api/articles?tag={encoded_query.replace(' ', '-')}&per_page={max_results}"
        
        response = requests.get(api_url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            articles = []
            
            for item in data[:max_results]:
                articles.append({
                    "title": item.get("title", ""),
                    "url": item.get("url", ""),
                    "author": item.get("user", {}).get("name", "Unknown"),
                    "tags": item.get("tag_list", [])
                })
            
            return articles
        else:
            # Fallback: try search endpoint
            try:
                search_url = f"https://dev.to/search/feed_content?per_page={max_results}&page=0&search_fields=&sort_by=hotness_score&sort_direction=desc&tag=&approved=&class_name=Article&q={encoded_query}"
                response = requests.get(search_url, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    articles = []
                    
                    for item in data.get("result", [])[:max_results]:
                        articles.append({
                            "title": item.get("title", ""),
                            "url": f"https://dev.to{item.get('path', '')}",
                            "author": item.get("user", {}).get("name", "Unknown"),
                            "tags": []
                        })
                    
                    return articles
            except:
                pass
            
            return []
            
    except Exception as e:
        print(f"Dev.to search error: {e}")
        return []


def search_medium_articles(query: str, max_results: int = 3) -> List[Dict[str, str]]:
    """
    Search Medium articles via Google search (Medium doesn't have public API).
    
    Args:
        query: Search query (pattern-based)
        max_results: Maximum number of results
    
    Returns:
        List of dicts with {title, url}
    """
    try:
        # Use Google search with site:medium.com
        encoded_query = urllib.parse.quote(f"site:medium.com {query}")
        search_url = f"https://www.google.com/search?q={encoded_query}&num={max_results}"
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        
        response = requests.get(search_url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            articles = []
            
            # Parse Google search results
            for result in soup.find_all('div', class_='g')[:max_results]:
                link_tag = result.find('a')
                title_tag = result.find('h3')
                
                if link_tag and title_tag:
                    url = link_tag.get('href', '')
                    if 'medium.com' in url:
                        articles.append({
                            "title": title_tag.get_text(),
                            "url": url,
                            "source": "Medium"
                        })
            
            return articles
        else:
            return []
            
    except Exception as e:
        print(f"Medium search error: {e}")
        return []


def get_external_knowledge(pattern_query: str) -> Dict[str, List[Dict]]:
    """
    Aggregate external knowledge from all sources.
    
    Args:
        pattern_query: Optimized search query for the pattern
    
    Returns:
        Dict with github_repos, stackoverflow_threads, dev_articles
    """
    print(f"🔍 Searching external knowledge for: {pattern_query}")
    
    return {
        "github_repos": search_github_repos(pattern_query),
        "stackoverflow_threads": search_stackoverflow(pattern_query),
        "dev_articles": search_dev_articles(pattern_query),
        "medium_articles": search_medium_articles(pattern_query)
    }
