# /my_career_portal/resume_builder_logic.py
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Flowable
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor
from reportlab.lib.enums import TA_LEFT, TA_JUSTIFY
import os
from dotenv import load_dotenv

load_dotenv()
GOOGLE_API_KEY_RESUME_AI = os.getenv("GOOGLE_API_KEY")

# --- Import Google Generative AI ---
genai_for_resume = None
try:
    import google.generativeai as genai
    if GOOGLE_API_KEY_RESUME_AI:
        genai.configure(api_key=GOOGLE_API_KEY_RESUME_AI)
        genai_for_resume = genai # Assign to the module alias we'll use
    else:
        print("WARNING (Resume AI): GOOGLE_API_KEY not set. AI summary feature disabled.")
except ImportError:
    print("WARNING (Resume AI): google-generativeai SDK not installed. AI summary feature disabled.")
except Exception as e:
    print(f"Error configuring Google AI for resume: {e}")

# --- Theme Colors and HRFlowable (Copy from your original resume_builder.py) ---
PRIMARY_COLOR = HexColor("#252b33")     
SECONDARY_COLOR = HexColor("#007acc")  
TEXT_COLOR = HexColor("#333333")        
SUBTLE_TEXT_COLOR = HexColor("#555555") 
BORDER_COLOR = HexColor("#cccccc")      
ACCENT_TEXT_COLOR = HexColor("#4A90E2")

class HRFlowable(Flowable):
    def __init__(self, width, thickness=0.6, color=BORDER_COLOR):
        Flowable.__init__(self)
        self.width = width
        self.thickness = thickness
        self.color = color
    def wrap(self, availWidth, availHeight):
        self.width = min(self.width, availWidth)
        return self.width, self.thickness
    def draw(self):
        self.canv.saveState()
        self.canv.setStrokeColor(self.color)
        self.canv.setLineWidth(self.thickness)
        self.canv.line(0, self.thickness / 2.0, self.width, self.thickness / 2.0)
        self.canv.restoreState()

# --- PDF Generation Function (Copied and adapted) ---
def generate_resume_pdf_from_data(data, filename="AI_Enhanced_Resume.pdf"):
    doc = SimpleDocTemplate(filename, pagesize=letter,
                            rightMargin=0.7*inch, leftMargin=0.7*inch,
                            topMargin=0.7*inch, bottomMargin=0.7*inch)
    story = []
    
    FONT_NAME = 'Helvetica'
    FONT_NAME_BOLD = 'Helvetica-Bold'
    FONT_NAME_ITALIC = 'Helvetica-Oblique'

    styles = {}
    styles['Name'] = ParagraphStyle('Name', fontName=FONT_NAME_BOLD, fontSize=26, leading=30,textColor=PRIMARY_COLOR, alignment=TA_LEFT, spaceBottom=0.08 * inch)
    # ... (COPY ALL YOUR STYLES DEFINITIONS HERE from original generate_resume_pdf) ...
    styles['ContactLine'] = ParagraphStyle('ContactLine', fontName=FONT_NAME, fontSize=9.5, leading=14,textColor=TEXT_COLOR, alignment=TA_LEFT, spaceBottom=0.03 * inch)
    styles['SectionTitle'] = ParagraphStyle('SectionTitle', fontName=FONT_NAME_BOLD, fontSize=13, leading=16,textColor=PRIMARY_COLOR, spaceBefore=0.22 * inch, spaceAfter=0.04 * inch)
    styles['Subheading'] = ParagraphStyle('Subheading', fontName=FONT_NAME_BOLD, fontSize=10.5, leading=14,textColor=SECONDARY_COLOR, spaceAfter=0.02 * inch)
    styles['AchievementTitle'] = ParagraphStyle('AchievementTitle', fontName=FONT_NAME_BOLD, fontSize=10, leading=13,textColor=SECONDARY_COLOR, spaceAfter=0.01 * inch)
    styles['MetaInfo'] = ParagraphStyle('MetaInfo', fontName=FONT_NAME, fontSize=9, leading=13,textColor=SUBTLE_TEXT_COLOR, spaceAfter=0.05 * inch)
    styles['BodyText'] = ParagraphStyle('BodyText', fontName=FONT_NAME, fontSize=9.5, leading=14,textColor=TEXT_COLOR, spaceAfter=0.05*inch, alignment=TA_JUSTIFY, wordWrap='CJK')
    styles['BulletPoint'] = ParagraphStyle('BulletPoint', parent=styles['BodyText'], bulletIndent=18, leftIndent=18,bulletText='• ', spaceAfter=0.03 * inch, alignment=TA_LEFT) # Added space after bullet
    styles['SkillsText'] = ParagraphStyle('SkillsText', parent=styles['BodyText'], alignment=TA_LEFT, leading=15, fontSize=9.5)
    styles['ProjectStack'] = ParagraphStyle('ProjectStack', fontName=FONT_NAME_ITALIC, fontSize=8.5,textColor=SUBTLE_TEXT_COLOR, leading=12, leftIndent=0,spaceBefore=0.02*inch, spaceAfter=0.04*inch)
    styles['CertificateDescription'] = ParagraphStyle('CertificateDescription', parent=styles['BodyText'], fontSize=9, leading=12, alignment=TA_LEFT,leftIndent=0, spaceBefore=0.01*inch, spaceAfter=0.03*inch)

    # --- Content Population (COPY THE LOGIC FROM YOUR ORIGINAL generate_resume_pdf) ---
    # Example: Personal Details
    if data.get('name'): story.append(Paragraph(data['name'].upper(), styles['Name']))
    contact_items = []
    if data.get('email'): contact_items.append(f"✉️ {data['email']}")
    if data.get('phone'): contact_items.append(f"📞 {data['phone']}")
    if data.get('location'): contact_items.append(f"📍 {data['location']}")
    if data.get('linkedin'):
        linkedin_url = data['linkedin']
        if not linkedin_url.startswith(('http://', 'https://')): linkedin_url = 'https://' + linkedin_url
        contact_items.append(f'<a href="{linkedin_url}" color="{ACCENT_TEXT_COLOR.hexval()}">🔗 LinkedIn</a>')
    if data.get('github'):
        github_url = data['github']
        if not github_url.startswith(('http://', 'https://')): github_url = 'https://' + github_url
        contact_items.append(f'<a href="{github_url}" color="{ACCENT_TEXT_COLOR.hexval()}">🔗 GitHub</a>')
    if contact_items:
        max_items_per_line = 3
        if len(contact_items) > max_items_per_line:
            story.append(Paragraph("  |  ".join(contact_items[:max_items_per_line]), styles['ContactLine']))
            if contact_items[max_items_per_line:]: # Check if there are items for the second line
                story.append(Paragraph("  |  ".join(contact_items[max_items_per_line:]), styles['ContactLine']))
        else:
            story.append(Paragraph("  |  ".join(contact_items), styles['ContactLine']))
    story.append(Spacer(1, 0.20 * inch))

    # --- Profile Summary ---
    if data.get('summary'):
        story.append(Paragraph("PROFILE SUMMARY", styles['SectionTitle']))
        story.append(HRFlowable(doc.width))
        story.append(Spacer(1, 0.1 * inch))
        story.append(Paragraph(data['summary'], styles['BodyText']))

    # --- Education ---
    if data.get('education'):
        story.append(Paragraph("EDUCATION", styles['SectionTitle']))
        story.append(HRFlowable(doc.width))
        story.append(Spacer(1, 0.1 * inch))
        for i, edu in enumerate(data.get('education', [])): # Ensure it's a list
            if edu.get('degree') and edu.get('institution'):
                if i > 0: story.append(Spacer(1, 0.1*inch))
                story.append(Paragraph(edu.get('degree','').upper(), styles['Subheading']))
                institution_info = f"{edu.get('institution','')}"
                if edu.get('year'): institution_info += f"  |  {edu.get('year','')}"
                story.append(Paragraph(institution_info, styles['MetaInfo']))
                if edu.get('details'): story.append(Paragraph(edu['details'], styles['BodyText']))
    
    # --- Work Experience ---
    if data.get('experience'):
        story.append(Paragraph("WORK EXPERIENCE", styles['SectionTitle']))
        story.append(HRFlowable(doc.width))
        story.append(Spacer(1, 0.1 * inch))
        for i, exp in enumerate(data.get('experience', [])):
            if exp.get('title') and exp.get('company'):
                if i > 0: story.append(Spacer(1, 0.1*inch))
                story.append(Paragraph(exp.get('title','').upper(), styles['Subheading']))
                company_info = f"{exp.get('company','')}"
                if exp.get('dates'): company_info += f"  |  {exp.get('dates','')}"
                story.append(Paragraph(company_info, styles['MetaInfo']))
                # Ensure exp['description'] is a list of strings (frontend JS should prepare this)
                if exp.get('description') and isinstance(exp.get('description'), list):
                    for point in exp['description']:
                        if point and point.strip(): story.append(Paragraph(point, styles['BulletPoint'])) # BulletPoint style adds the '• '
    
    # --- Projects ---
    if data.get('projects'):
        story.append(Paragraph("PROJECTS", styles['SectionTitle']))
        story.append(HRFlowable(doc.width))
        story.append(Spacer(1, 0.1 * inch))
        for i, proj in enumerate(data.get('projects', [])):
            if proj.get('title'):
                if i > 0: story.append(Spacer(1, 0.1*inch))
                story.append(Paragraph(proj.get('title','').upper(), styles['Subheading']))
                # Ensure proj['stack'] is a list (backend Flask app will prepare this from stack_str)
                if proj.get('stack') and isinstance(proj['stack'], list) and proj['stack']:
                    story.append(Paragraph(f"Tech Stack: {', '.join(proj['stack'])}", styles['ProjectStack']))
                # Ensure proj['description'] is a list
                if proj.get('description') and isinstance(proj.get('description'), list):
                    for point in proj['description']:
                        if point and point.strip(): story.append(Paragraph(point, styles['BulletPoint']))

    # --- Skills ---
    if data.get('skills'): # Expects data['skills'] to be a list
        header_text = data.get('skills_tools_header', "SKILLS").upper()
        story.append(Paragraph(header_text, styles['SectionTitle']))
        story.append(HRFlowable(doc.width))
        story.append(Spacer(1, 0.1 * inch))
        if isinstance(data['skills'], list) and data['skills']:
            # Create a single paragraph with bullets for skills, more compact
            skills_paragraph_text = "   ".join([f"• {skill}" for skill in data['skills']])
            story.append(Paragraph(skills_paragraph_text, styles['SkillsText']))
            # Or use multiple paragraphs if you prefer one skill per line with BulletPoint style:
            # for skill_item in data['skills']:
            #     story.append(Paragraph(skill_item, styles['BulletPoint']))


    # --- Certificates ---
    if data.get('certificates'):
        story.append(Paragraph("CERTIFICATES", styles['SectionTitle']))
        story.append(HRFlowable(doc.width))
        story.append(Spacer(1, 0.1 * inch))
        for i, cert in enumerate(data.get('certificates',[])):
            if cert.get('name'):
                if i > 0: story.append(Spacer(1, 0.1*inch))
                story.append(Paragraph(cert.get('name','').upper(), styles['Subheading']))
                meta_parts = []
                if cert.get('issuer'): meta_parts.append(cert.get('issuer',''))
                if cert.get('date'): meta_parts.append(cert.get('date',''))
                if meta_parts: story.append(Paragraph("  |  ".join(meta_parts), styles['MetaInfo']))
                if cert.get('description'): # This could be a URL or short text
                    desc_text = cert.get('description','')
                    if desc_text.startswith(('http://', 'https://')):
                        story.append(Paragraph(f'<a href="{desc_text}" color="{ACCENT_TEXT_COLOR.hexval()}">View Certificate/Details</a>', styles['CertificateDescription']))
                    elif desc_text.strip():
                        story.append(Paragraph(desc_text, styles['CertificateDescription']))
    
    # --- Achievements ---
    if data.get('achievements'):
        story.append(Paragraph("ACHIEVEMENTS", styles['SectionTitle']))
        story.append(HRFlowable(doc.width))
        story.append(Spacer(1, 0.1 * inch))
        for i, ach in enumerate(data.get('achievements',[])):
            # description_str is expected to be newline separated, split it into points
            description_points = []
            if ach.get('description_str') and isinstance(ach.get('description_str'), str):
                description_points = [p.strip() for p in ach.get('description_str').split('\n') if p.strip()]
            
            if description_points: # Only add if description exists
                if i > 0: story.append(Spacer(1, 0.05*inch))
                if ach.get('title'):
                    story.append(Paragraph(ach.get('title','').upper(), styles['AchievementTitle']))
                if ach.get('context_date'):
                    story.append(Paragraph(ach.get('context_date',''), styles['MetaInfo']))
                for point in description_points:
                    story.append(Paragraph(point, styles['BulletPoint']))
    try:
        doc.build(story)
        print(f"Resume PDF generated successfully: {filename}")
        return filename
    except Exception as e:
        print(f"ERROR generating PDF for resume: {e}")
        import traceback
        traceback.print_exc()
        return None

# --- AI Content Generation Function (Copied and adapted) ---
def generate_ai_summary_for_resume(keywords, experience_highlights, api_key_override=None):
    # Use genai_for_resume (which is the configured genai module alias)
    current_api_key = api_key_override if api_key_override else GOOGLE_API_KEY_RESUME_AI
    if not genai_for_resume:
        return "AI features disabled: Google Generative AI SDK not available or not configured."
    if not current_api_key:
        return f"AI features disabled: Google API Key not provided. (Placeholder: Highly motivated individual with skills in {', '.join(keywords)} and experience in {experience_highlights}.)"
    
    try:
        # Ensure genai_for_resume is configured with the key if an override is passed
        # This is a bit redundant if it's already configured at module load, but safe
        if api_key_override and api_key_override != genai_for_resume.API_KEY: # Check if key is different
             genai_for_resume.configure(api_key=api_key_override)

        model = genai_for_resume.GenerativeModel(model_name="gemini-1.5-flash-latest") # Or your preferred model
        prompt_parts = [
            "Generate a professional and concise profile summary for a resume, strictly 2-4 sentences long.",
            "Incorporate the following details:",
            f"Key Skills: {', '.join(keywords) if keywords else 'Not specified'}.",
            f"Experience Highlights or Career Goals: {experience_highlights if experience_highlights else 'Not specified'}.",
            "The summary should be engaging and tailored for a resume. Avoid first-person pronouns like 'I' or 'My' unless absolutely natural and professional.",
            "Focus on what the candidate brings to a potential employer.",
            "Example: 'Dynamic and results-oriented Software Engineer with expertise in Python, Java, and cloud computing. Proven ability in developing scalable web applications and leading cross-functional teams. Seeking to leverage these skills to drive innovation at a forward-thinking company.'"
        ]
        prompt = "\n".join(prompt_parts)
        # Standard safety settings from your original code
        safety_settings=[
            {"category": c, "threshold": "BLOCK_MEDIUM_AND_ABOVE"} 
            for c in ["HARM_CATEGORY_HARASSMENT", "HARM_CATEGORY_HATE_SPEECH", "HARM_CATEGORY_SEXUALLY_EXPLICIT", "HARM_CATEGORY_DANGEROUS_CONTENT"]
        ]
        generation_config = genai_for_resume.types.GenerationConfig(temperature=0.7, max_output_tokens=250)
        
        response = model.generate_content(prompt, generation_config=generation_config, safety_settings=safety_settings)
        
        if response.parts:
            return response.text.strip()
        elif response.prompt_feedback and response.prompt_feedback.block_reason:
             block_reason_msg = getattr(response.prompt_feedback, 'block_reason_message', str(response.prompt_feedback.block_reason))
             print(f"Resume AI summary blocked: {block_reason_msg}")
             return f"Content generation blocked by safety filters: {block_reason_msg}. Please revise your input."
        else:
            # Attempt to get more detailed error if available for candidate issues
            try:
                candidate_error = response.candidates[0].finish_reason if response.candidates else "Unknown"
                if candidate_error != "STOP": # Check if not a normal stop
                    return f"Error generating summary (Model Finish Reason: {candidate_error}). Please try again or write manually."
            except: pass # Ignore if candidates attribute is not as expected
            print("Resume AI summary failed: No content returned for unknown reason.")
            return "Error generating summary. Please write manually or try again."
    except Exception as e:
        print(f"Resume AI summary generation failed: {e}")
        return f"Error generating summary: {str(e)}. Please write manually."