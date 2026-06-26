import streamlit as st
from typing import Callable, Optional, Tuple

def create(
    left_content: Callable[[], None], 
    right_content: Callable[[], None], 
    left_width: int = 1, 
    right_width: int = 1,
    gap: Optional[str] = None
) -> Tuple[st.container, st.container]:
    """
    Creates a two-column layout with customizable widths.
    
    This function creates a two-column layout using Streamlit's columns feature.
    It takes two functions that define the content for each column and returns
    the column containers for further manipulation if needed.
    
    Args:
        left_content: Function that populates the left column
        right_content: Function that populates the right column
        left_width: Relative width of the left column (default: 1)
        right_width: Relative width of the right column (default: 1)
        gap: Optional CSS gap between columns (e.g., "1rem")
        
    Returns:
        Tuple containing the left and right column containers
        
    Example:
        ```python
        def left_column():
            st.header("Left Column")
            st.write("This is the left column content")
            
        def right_column():
            st.header("Right Column")
            st.write("This is the right column content")
            
        left, right = two_column.create(left_column, right_column, 2, 1)
        ```
    """
    # Create columns with specified widths
    if gap:
        # Use custom CSS for gap if specified
        st.markdown(f"""
        <style>
        .stColumns > div {{
            gap: {gap};
        }}
        </style>
        """, unsafe_allow_html=True)
    
    left_col, right_col = st.columns([left_width, right_width])
    
    # Populate the columns with content
    with left_col:
        left_content()
        
    with right_col:
        right_content()
        
    return left_col, right_col
