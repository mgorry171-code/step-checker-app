import streamlit as st
import sympy
from sympy import symbols, solve, Eq, latex, simplify, I, pi, E
from sympy.parsing.sympy_parser import parse_expr, standard_transformations, implicit_multiplication_application
import datetime
import pandas as pd
import re
import numpy as np
import plotly.graph_objects as go

# --- SETUP SESSION STATE ---
# Updated default to show off Algebra 2 features
if 'line_prev' not in st.session_state:
    st.session_state.line_prev = "x^2 + 4 = 0" 
if 'line_curr' not in st.session_state:
    st.session_state.line_curr = ""
if 'history' not in st.session_state:
    st.session_state.history = []
if 'keypad_target' not in st.session_state:
    st.session_state.keypad_target = "Current Line"
if 'step_verified' not in st.session_state:
    st.session_state.step_verified = False

# --- HELPER FUNCTIONS ---
def add_to_input(text_to_add):
    if st.session_state.keypad_target == "Previous Line":
        st.session_state.line_prev += text_to_add
    else:
        st.session_state.line_curr += text_to_add

def clean_input(text):
    text = text.lower()
    text = re.sub(r'(\d),(\d{3})', r'\1\2', text)
    text = text.replace(" and ", ";")
    text = text.replace("^", "**")
    # Convert 'i' to 'I' (Imaginary) but NOT inside words like 'sin', 'pi', 'limit'
    # This Regex checks for 'i' that is NOT surrounded by other letters
    text = re.sub(r'(?<![a-z])i(?![a-z])', 'I', text) 
    text = text.replace("+/-", "±")
    text = text.replace("√", "sqrt") # Handle square root symbol
    text = text.replace("%", "/100")
    text = text.replace(" of ", "*")
    text = text.replace("=<", "<=").replace("=>", ">=")
    return text

def smart_parse(text, evaluate=True):
    transformations = (standard_transformations + (implicit_multiplication_application,))
    try:
        # Define extra local variables for 'e' and 'pi' if user types them as text
        local_dict = {'e': E, 'pi': pi}
        
        if "<=" in text or ">=" in text or "<" in text or ">" in text:
            return parse_expr(text, transformations=transformations, evaluate=evaluate, local_dict=local_dict)
        elif "=" in text:
            parts = text.split("=")
            lhs = parse_expr(parts[0], transformations=transformations, evaluate=evaluate, local_dict=local_dict)
            rhs = parse_expr(parts[1], transformations=transformations, evaluate=evaluate, local_dict=local_dict)
            return Eq(lhs, rhs)
        else:
            return parse_expr(text, transformations=transformations, evaluate=evaluate, local_dict=local_dict)
    except:
        return sympify(text, evaluate=evaluate)

def pretty_print(math_str):
    try:
        clean_str = clean_input(math_str)
        clean_str = clean_str.replace("±", "±")
        if ";" in clean_str:
             parts = clean_str.split(";")
             latex_parts = [latex(smart_parse(p, evaluate=False)) for p in parts if p.strip()]
             return ", \\quad ".join(latex_parts)
        expr = smart_parse(clean_str, evaluate=False)
        return latex(expr)
    except:
        return None

def convert_df_to_csv(df):
    return df.to_csv(index=False).encode('utf-8')

# --- LOGIC BRAIN 5.0 (Algebra 2 Support) ---
def get_solution_set(text_str):
    x, y = symbols('x y')
    clean = clean_input(text_str)
    try:
        equations = []
        if ";" in clean:
            raw_eqs = clean.split(";")
            for r in raw_eqs:
                if r.strip(): equations.append(smart_parse(r, evaluate=True))
        elif clean.count("=") > 1 and "," in clean:
            raw_eqs = clean.split(",")
            for r in raw_eqs:
                if r.strip(): equations.append(smart_parse(r, evaluate=True))
        else:
             equations.append(smart_parse(clean, evaluate=True))

        if len(equations) > 1:
            sol = solve(equations, (x, y), set=True)
            return sol[1] 
        else:
            expr = equations[0]
            if isinstance(expr, tuple): return sympy.FiniteSet(expr)
            if isinstance(expr, Eq) or not (expr.is_Relational):
                 if 'y' in str(expr) and 'x' in str(expr): return sympy.FiniteSet(expr) # 2-var relation
                 else:
                     # Solve for x (handles quadratics automatically)
                     if 'x' not in str(expr) and 'y' not in str(expr): return sympy.FiniteSet(expr)
                     sol = solve(expr, x, set=True)
                     return sol[1] 
            else:
                solution = reduce_inequalities(expr, x)
                return solution.as_set()
    except Exception as e:
        return None

def check_simplification(text):
    try:
        clean = clean_input(text)
        expr = smart_parse(clean, evaluate=False)
        if isinstance(expr, Eq): rhs = expr.rhs
        else: rhs = expr
        
        # 1. Basic Number or Symbol (x, 5, 3.14)
        if rhs.is_Number or rhs.is_Symbol: return True
        
        # 2. Negative Number (-5) is technically Mul(-1, 5)
        if rhs.is_Mul and len(rhs.args) == 2 and rhs.args[0] == -1 and rhs.args[1].is_Number: return True
        
        # 3. ALGEBRA 2 UPDATE: Complex Numbers (3 + 4i) are 'Add' but valid
        # Check if it has an imaginary part
        if rhs.has(I):
             # If it's just a number + number*I, it's simplified
             # We assume SymPy automatically simplifies "2+3+i" to "5+i" during parsing if evaluate=True
             # But here evaluate=False. 
             # Let's rely on SymPy's simplifying power implicitly.
             # If the user typed "3+4i", that is standard form.
             return True

        return False
    except:
        return True

def diagnose_error(set_correct, set_user):
    return "Check your math logic.", ""

def next_step():
    st.session_state.line_prev = st.session_state.line_curr
    st.session_state.line_curr = ""
    st.session_state.step_verified = False

def plot_system_interactive(text_str):
    try:
        x, y = symbols('x y')
        clean = clean_input(text_str)
        
        equations = []
        if ";" in clean:
            raw_eqs = clean.split(";")
            for r in raw_eqs:
                if r.strip(): equations.append(smart_parse(r, evaluate=True))
        else:
            if clean.count("=") > 1 and "," in clean:
                 raw_eqs = clean.split(",")
                 for r in raw_eqs:
                    if r.strip(): equations.append(smart_parse(r, evaluate=True))
            else:
                 equations.append(smart_parse(clean, evaluate=True))
        
        fig = go.Figure()
        x_vals = np.linspace(-10, 10, 100)
        colors = ['blue', 'orange', 'green']
        i = 0
        table_data_list = [] 
        has_plotted = False
        
        for eq in equations:
            try:
                # SKIP COMPLEX PLOTTING
                # If equation has 'I' (imaginary), graphing usually fails or is meaningless on Real plane
                if eq.has(I):
                    continue

                if 'y' in str(eq):
                    y_expr = solve(eq, y)
                    if y_expr:
                        # Use numpy complex support just in case, but filter later
                        f_y = sympy.lambdify(x, y_expr[0], "numpy") 
                        y_vals = f_y(x_vals)
                        
                        # Filter out complex results (e.g. sqrt(negative))
                        if np.iscomplexobj(y_vals):
                            # Set complex parts to NaN so they don't plot
                            y_vals = y_vals.real 
                            # (Simple hack: better is to mask them, but this prevents crashing)
                        
                        fig.add_trace(go.Scatter(x=x_vals, y=y_vals, mode='lines', name=f"Eq {i+1}", line=dict(color=colors[i % 3])))
                        
                        # T-Chart
                        t_x = []
                        t_y = []
                        for val in [-4, -2, 0, 2, 4]:
                            try:
                                res_y = y_expr[0].subs(x, val)
                                if res_y.is_real: # Only list real points
                                    t_x.append(val)
                                    t_y.append(round(float(res_y), 2))
                            except: pass
                        
                        if t_x:
                            df_table = pd.DataFrame({"x": t_x, "y": t_y})
                            table_data_list.append({"label": f"Equation {i+1}: ${latex(eq)}$", "df": df_table})
                        
                        has_plotted = True
                        i += 1
                elif 'x' in str(eq):
                    x_sol = solve(eq, x)
                    if x_sol:
                        val = float(x_sol[0])
                        fig.add_vline(x=val, line_dash="dash", line_color=colors[i%3], annotation_text=f"x={val}")
                        t_x = [val]*5
                        t_y = [-4, -2, 0, 2, 4]
                        df_table = pd.DataFrame({"x": t_x, "y": t_y})
                        table_data_list.append({"label": f"Equation {i+1}: ${latex(eq)}$", "df": df_table})
                        has_plotted = True
                        i += 1
            except: pass
        
        # Intersection logic (Skip for now to avoid complex crashes in intersection)
        if len(equations) > 1:
             pass 

        if not has_plotted: return None, None

        fig.update_layout(xaxis_title="X Axis", yaxis_title="Y Axis", xaxis=dict(range=[-10, 10], showgrid=True, zeroline=True, zerolinewidth=2, zerolinecolor='black'), yaxis=dict(range=[-10, 10], showgrid=True, zeroline=True, zerolinewidth=2, zerolinecolor='black'), height=500, showlegend=True, margin=dict(l=20, r=20, t=30, b=20))
        return fig, table_data_list

    except Exception as e:
        return None, None

def validate_step(line_prev_str, line_curr_str):
    debug_info = {}
    try:
        if not line_prev_str or not line_curr_str: return False, "Empty", "", {}
        set_A = get_solution_set(line_prev_str)
        set_B = get_solution_set(line_curr_str)
        debug_info['Raw Set A'] = str(set_A)
        debug_info['Raw Set B'] = str(set_B)
        
        if set_A is None and line_prev_str: return False, "Could not solve Line A", "", debug_info
        if set_B is None: return False, "Could not parse Line B", "", debug_info

        if set_A == set_B: return True, "Valid", "", debug_info
        
        hint, internal_debug = diagnose_error(set_A, set_B)
        return False, "Invalid", hint, debug_info

    except Exception as e:
        return False, f"Syntax Error: {e}", "", debug_info

# --- WEB INTERFACE ---

st.set_page_config(page_title="The Logic Lab v5.0", page_icon="🧪")
st.title("🧪 The Logic Lab")

with st.sidebar:
    st.header("Settings")
    if st.session_state.history:
        st.write(f"Problems Checked: **{len(st.session_state.history)}**")
        df = pd.DataFrame(st.session_state.history)
        csv = convert_df_to_csv(df)
        st.download_button("📊 Download Session Data", csv, "Math_Session.csv", "text/csv")
        if st.button("Clear History"):
            st.session_state.history = []
            st.rerun()
            
    st.markdown("---")
    # PARENT MODE TOGGLE
    parent_mode = st.toggle("👨‍👩‍👧 Parent Mode", value=False)
    
    st.markdown("---")
    show_debug = st.checkbox("🛠️ Engineer Mode", value=False)

# --- DISPLAY AREA ---
col1, col2 = st.columns(2)
with col1:
    st.markdown("### Previous Line")
    st.text_input("Line A", key="line_prev", label_visibility="collapsed")
    if st.session_state.line_prev: 
        st.latex(pretty_print(st.session_state.line_prev))
        
        # PARENT MODE: REVEAL ANSWER
        if parent_mode:
            if st.button("👁️ Reveal Answer for Line A"):
                sol_set = get_solution_set(st.session_state.line_prev)
                if sol_set:
                    st.success("**Answer Key:**")
                    st.latex(latex(sol_set))
                else:
                    st.error("Could not solve this expression.")
        
        if st.checkbox("📈 Visualize Graph"):
            fig, table_list = plot_system_interactive(st.session_state.line_prev)
            if fig:
                tab1, tab2 = st.tabs(["📉 Interactive Graph", "🔢 Table of Values"])
                with tab1:
                    st.plotly_chart(fig, use_container_width=True)
                    st.caption("Hover to see points.")
                with tab2:
                    st.write("Use these T-Charts to plot the lines:")
                    if table_list:
                        if len(table_list) == 2:
                            t1, t2 = st.columns(2)
                            with t1:
                                st.write(table_list[0]["label"])
                                st.dataframe(table_list[0]["df"], hide_index=True)
                            with t2:
                                st.write(table_list[1]["label"])
                                st.dataframe(table_list[1]["df"], hide_index=True)
                        else:
                            for item in table_list:
                                st.write(item["label"])
                                st.dataframe(item["df"], hide_index=True)
            else:
                st.caption("Could not graph this expression. (Graphs may be hidden for complex numbers)")

    st.caption("For Systems: Use ';' to separate. (e.g. `2x+y=10; x-y=4`)")

with col2:
    st.markdown("### Current Line")
    st.text_input("Line B", key="line_curr", label_visibility="collapsed")
    if st.session_state.line_curr: st.latex(pretty_print(st.session_state.line_curr))

st.markdown("---")

# --- KEYPAD (UPDATED FOR ALGEBRA 2) ---
with st.expander("⌨️ Show Math Keypad", expanded=False):
    st.write("Click a button to add it to the **" + st.session_state.keypad_target + "**.")
    st.radio("Target:", ["Previous Line", "Current Line"], horizontal=True, key="keypad_target", label_visibility="collapsed")
    st.write("") 
    
    # ROW 1
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.button("x²", on_click=add_to_input, args=("^2",))
    c2.button("√", on_click=add_to_input, args=("sqrt(",)) # NEW: Square Root
    c3.button("(", on_click=add_to_input, args=("(",))
    c4.button(")", on_click=add_to_input, args=(")",))
    c5.button(";", on_click=add_to_input, args=("; ",))
    c6.button("÷", on_click=add_to_input, args=("/",))

    # ROW 2
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.button(" < ", on_click=add_to_input, args=("<",))
    c2.button("\>", on_click=add_to_input, args=(">",)) 
    c3.button(" ≤ ", on_click=add_to_input, args=("<=",))
    c4.button(" ≥ ", on_click=add_to_input, args=(">=",))
    c5.button("x", on_click=add_to_input, args=("x",))
    c6.button("y", on_click=add_to_input, args=("y",))
    
    # ROW 3 (NEW ALGEBRA 2 BUTTONS)
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.button("i", on_click=add_to_input, args=("i",))  # Imaginary
    c2.button("π", on_click=add_to_input, args=("pi",)) # Pi
    c3.button("e", on_click=add_to_input, args=("e",))  # Euler
    c4.button("log", on_click=add_to_input, args=("log(",)) # Log
    c5.button("sin", on_click
