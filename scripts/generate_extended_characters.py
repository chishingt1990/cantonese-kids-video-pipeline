# scripts/generate_extended_characters.py
import os

EXTENDED_SVG = {
    "grandparents_paternal": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 360 320" width="100%" height="100%">
  <!-- Paternal Grandparents: 爺爺 (Checkered polo, wire glasses) & 嫲嫲 (Bob cut, gold glasses, magenta top) -->
  <ellipse cx="180" cy="295" rx="120" ry="16" fill="#0f172a" opacity="0.12"/>
  
  <!-- 爺爺 (Grandpa Left) -->
  <g id="yeye">
    <!-- Body: Blue Checkered Polo -->
    <rect x="55" y="155" width="100" height="130" rx="20" fill="#0284c7" stroke="#0f172a" stroke-width="3.5"/>
    <path d="M 80 155 L 80 285 M 110 155 L 110 285 M 130 155 L 130 285" stroke="#38bdf8" stroke-width="2"/>
    <path d="M 55 185 L 155 185 M 55 215 L 155 215 M 55 245 L 155 245" stroke="#38bdf8" stroke-width="2"/>
    <!-- Dark Collar -->
    <path d="M 85 155 L 105 175 L 125 155 Z" fill="#1e293b" stroke="#0f172a" stroke-width="2.5"/>
    
    <!-- Head -->
    <circle cx="105" cy="100" r="40" fill="#fed7aa" stroke="#0f172a" stroke-width="3.5"/>
    <!-- Sleek Salt-and-Pepper Combed Hair -->
    <path d="M 68 95 Q 65 58 105 54 Q 145 58 142 95 C 132 80 120 74 105 74 C 90 74 78 80 68 95 Z" fill="#475569" stroke="#0f172a" stroke-width="3.5"/>
    
    <!-- Thin Rectangular Black Wire Glasses -->
    <rect x="80" y="90" width="22" height="18" rx="4" fill="none" stroke="#0f172a" stroke-width="3"/>
    <rect x="108" y="90" width="22" height="18" rx="4" fill="none" stroke="#0f172a" stroke-width="3"/>
    <line x1="102" y1="99" x2="108" y2="99" stroke="#0f172a" stroke-width="2.5"/>
    <circle cx="91" cy="99" r="3.5" fill="#0f172a"/>
    <circle cx="119" cy="99" r="3.5" fill="#0f172a"/>
    
    <!-- Gentle Smile -->
    <path d="M 92 122 Q 105 132 118 122" fill="none" stroke="#0f172a" stroke-width="3" stroke-linecap="round"/>
  </g>

  <!-- 嫲嫲 (Grandma Right) -->
  <g id="mama">
    <!-- Body: Magenta Top with white inner sleeves -->
    <rect x="205" y="160" width="95" height="125" rx="20" fill="#c026d3" stroke="#0f172a" stroke-width="3.5"/>
    <path d="M 230 190 Q 252 205 275 190" fill="none" stroke="#f0abfc" stroke-width="3"/>
    <path d="M 235 220 Q 252 235 270 220" fill="none" stroke="#f0abfc" stroke-width="3"/>
    
    <!-- Head -->
    <circle cx="252" cy="102" r="38" fill="#fed7aa" stroke="#0f172a" stroke-width="3.5"/>
    <!-- Short Brown-Grey Bob Cut with Bangs -->
    <path d="M 214 108 Q 210 62 252 58 Q 294 62 290 108 C 282 94 268 84 252 84 C 236 84 222 94 214 108 Z" fill="#57534e" stroke="#0f172a" stroke-width="3.5"/>
    
    <!-- Delicate Gold-Rimmed Oval Glasses -->
    <ellipse cx="238" cy="100" rx="12" ry="10" fill="none" stroke="#d97706" stroke-width="2.5"/>
    <ellipse cx="266" cy="100" rx="12" ry="10" fill="none" stroke="#d97706" stroke-width="2.5"/>
    <line x1="250" y1="100" x2="254" y2="100" stroke="#d97706" stroke-width="2"/>
    <circle cx="238" cy="100" r="3.5" fill="#0f172a"/>
    <circle cx="266" cy="100" r="3.5" fill="#0f172a"/>
    
    <!-- Joyful Cheeks & Smile -->
    <circle cx="228" cy="112" r="7" fill="#f43f5e" opacity="0.35"/>
    <circle cx="276" cy="112" r="7" fill="#f43f5e" opacity="0.35"/>
    <path d="M 242 120 Q 252 132 262 120" fill="none" stroke="#0f172a" stroke-width="3" stroke-linecap="round"/>
  </g>
</svg>""",

    "grandparents_maternal": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 360 320" width="100%" height="100%">
  <!-- Maternal Grandparents: 公公 (Buzz cut, white tee) & 婆婆 (Pixie cut with bangs, round joyful smile) -->
  <ellipse cx="180" cy="295" rx="120" ry="16" fill="#0f172a" opacity="0.12"/>
  
  <!-- 公公 (Grandpa Left) -->
  <g id="gonggong">
    <!-- Body: White Graphic Tee -->
    <rect x="55" y="155" width="100" height="130" rx="20" fill="#f8fafc" stroke="#0f172a" stroke-width="3.5"/>
    <path d="M 85 155 Q 105 170 125 155" fill="none" stroke="#0f172a" stroke-width="3"/>
    
    <!-- Head -->
    <circle cx="105" cy="100" r="40" fill="#fed7aa" stroke="#0f172a" stroke-width="3.5"/>
    <!-- Close-Cropped Buzz Cut Hair -->
    <path d="M 68 92 Q 66 62 105 58 Q 144 62 142 92 Z" fill="#94a3b8" stroke="#0f172a" stroke-width="3"/>
    
    <!-- Arched Brows & Gentle Eyes -->
    <path d="M 84 85 Q 92 78 100 85" fill="none" stroke="#0f172a" stroke-width="3" stroke-linecap="round"/>
    <path d="M 110 85 Q 118 78 126 85" fill="none" stroke="#0f172a" stroke-width="3" stroke-linecap="round"/>
    <circle cx="92" cy="96" r="4" fill="#0f172a"/>
    <circle cx="118" cy="96" r="4" fill="#0f172a"/>
    
    <!-- Warm Serene Smile -->
    <path d="M 94 118 Q 105 128 116 118" fill="none" stroke="#0f172a" stroke-width="3" stroke-linecap="round"/>
  </g>

  <!-- 婆婆 (Grandma Right) -->
  <g id="popo">
    <!-- Body: Clean White Tee with Beaded Bracelet -->
    <rect x="205" y="160" width="95" height="125" rx="20" fill="#f8fafc" stroke="#0f172a" stroke-width="3.5"/>
    <!-- Beaded Bracelet on Wrist -->
    <circle cx="202" cy="235" r="3.5" fill="#b45309"/>
    <circle cx="202" cy="243" r="3.5" fill="#b45309"/>
    <circle cx="202" cy="251" r="3.5" fill="#b45309"/>
    
    <!-- Head -->
    <circle cx="252" cy="102" r="38" fill="#fed7aa" stroke="#0f172a" stroke-width="3.5"/>
    <!-- Pixie Cut with Soft Textured Bangs -->
    <path d="M 216 102 Q 212 65 252 60 Q 292 65 288 102 C 282 90 270 82 252 82 C 234 82 222 90 216 102 Z" fill="#78716c" stroke="#0f172a" stroke-width="3.5"/>
    <path d="M 232 82 Q 242 94 252 86 Q 262 94 272 82" fill="none" stroke="#0f172a" stroke-width="2.5"/>
    
    <!-- Kind Smiling Eyes -->
    <ellipse cx="240" cy="98" rx="5" ry="6" fill="#0f172a"/>
    <circle cx="238" cy="95" r="2" fill="#ffffff"/>
    <ellipse cx="264" cy="98" rx="5" ry="6" fill="#0f172a"/>
    <circle cx="262" cy="95" r="2" fill="#ffffff"/>
    
    <!-- Round Cheeks & Wide Joyful Smile -->
    <circle cx="230" cy="110" r="8" fill="#f43f5e" opacity="0.35"/>
    <circle cx="274" cy="110" r="8" fill="#f43f5e" opacity="0.35"/>
    <path d="M 242 118 Q 252 130 262 118" fill="none" stroke="#0f172a" stroke-width="3" stroke-linecap="round"/>
  </g>
</svg>""",

    "auntie_cousins": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 380 320" width="100%" height="100%">
  <!-- Auntie (姑媽 with glasses) & Cousins (表哥 Ryan with sporty glasses, and 表弟 with sunglasses) -->
  <ellipse cx="190" cy="295" rx="140" ry="16" fill="#0f172a" opacity="0.12"/>

  <!-- 姑媽 (Auntie Center-Left) -->
  <g id="auntie">
    <rect x="110" y="145" width="85" height="135" rx="18" fill="#d4d4d8" stroke="#0f172a" stroke-width="3.5"/>
    <!-- Head -->
    <circle cx="152" cy="95" r="36" fill="#fed7aa" stroke="#0f172a" stroke-width="3.5"/>
    <!-- Hair Tied Back with Bangs -->
    <path d="M 118 95 Q 116 58 152 54 Q 188 58 186 95 C 178 85 166 78 152 78 C 138 78 126 85 118 95 Z" fill="#1c1917" stroke="#0f172a" stroke-width="3.5"/>
    <ellipse cx="188" cy="95" rx="6" ry="10" fill="#1c1917"/> <!-- Hair bun -->
    <!-- Chic Dark Glasses -->
    <rect x="132" y="86" width="18" height="15" rx="4" fill="none" stroke="#0f172a" stroke-width="3"/>
    <rect x="156" y="86" width="18" height="15" rx="4" fill="none" stroke="#0f172a" stroke-width="3"/>
    <line x1="150" y1="93" x2="156" y2="93" stroke="#0f172a" stroke-width="2.5"/>
    <circle cx="141" cy="93" r="3" fill="#0f172a"/>
    <circle cx="165" cy="93" r="3" fill="#0f172a"/>
    <!-- Smile -->
    <path d="M 142 112 Q 152 122 162 112" fill="none" stroke="#0f172a" stroke-width="3" stroke-linecap="round"/>
  </g>

  <!-- 表哥 Ryan (Older Cousin Left - Energetic boy with glasses) -->
  <g id="ryan">
    <!-- Athletic Under Armour style shirt -->
    <rect x="35" y="180" width="70" height="95" rx="14" fill="#0284c7" stroke="#0f172a" stroke-width="3"/>
    <!-- Head -->
    <circle cx="70" cy="135" r="30" fill="#fed7aa" stroke="#0f172a" stroke-width="3"/>
    <!-- Short Boy Hair -->
    <path d="M 42 135 Q 40 102 70 98 Q 100 102 98 135 C 92 125 82 118 70 118 C 58 118 48 125 42 135 Z" fill="#1c1917" stroke="#0f172a" stroke-width="3"/>
    <!-- Sporty Glasses -->
    <rect x="52" y="128" width="16" height="13" rx="3" fill="none" stroke="#10b981" stroke-width="2.5"/>
    <rect x="72" y="128" width="16" height="13" rx="3" fill="none" stroke="#10b981" stroke-width="2.5"/>
    <line x1="68" y1="134" x2="72" y2="134" stroke="#10b981" stroke-width="2"/>
    <circle cx="60" cy="134" r="2.5" fill="#0f172a"/>
    <circle cx="80" cy="134" r="2.5" fill="#0f172a"/>
    <!-- Big Adventurous Smile -->
    <path d="M 60 148 Q 70 158 80 148" fill="none" stroke="#0f172a" stroke-width="2.5" stroke-linecap="round"/>
  </g>

  <!-- 表弟 (Younger Cousin Right - Toddler with sunglasses) -->
  <g id="cousin_younger">
    <!-- Blue Toddler Tee -->
    <rect x="235" y="195" width="65" height="85" rx="14" fill="#3b82f6" stroke="#0f172a" stroke-width="3"/>
    <!-- Head -->
    <circle cx="267" cy="155" r="28" fill="#fed7aa" stroke="#0f172a" stroke-width="3"/>
    <!-- Cute toddler hair -->
    <path d="M 241 155 Q 240 125 267 122 Q 294 125 293 155 Z" fill="#292524" stroke="#0f172a" stroke-width="3"/>
    <!-- Cool Blue Toddler Sunglasses (from photo!) -->
    <rect x="250" y="148" width="16" height="12" rx="4" fill="#0284c7" stroke="#1e3a8a" stroke-width="2"/>
    <rect x="270" y="148" width="16" height="12" rx="4" fill="#0284c7" stroke="#1e3a8a" stroke-width="2"/>
    <line x1="266" y1="154" x2="270" y2="154" stroke="#1e3a8a" stroke-width="2"/>
    <!-- Giggly Smile -->
    <path d="M 258 168 Q 267 176 276 168" fill="none" stroke="#0f172a" stroke-width="2.5" stroke-linecap="round"/>
  </g>
</svg>"""
}

for k, v in EXTENDED_SVG.items():
    p = f"assets/characters/{k}.svg"
    with open(p, "w", encoding="utf-8") as f:
        f.write(v.strip())
    print(f"Generated {p}")
