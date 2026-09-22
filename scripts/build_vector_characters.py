# scripts/build_vector_characters.py
import os

CHARACTERS_SVG = {
    "levi": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 300 400" width="100%" height="100%">
  <!-- Levi: Older Twin Brother (哥哥) -->
  <!-- Proportions: 1-2 year old toddler, chubby round cheeks, bold red polo, straight bangs fringe -->
  <defs>
    <radialGradient id="leviCheek" cx="50%" cy="50%" r="50%">
      <stop offset="0%" stop-color="#f43f5e" stop-opacity="0.35"/>
      <stop offset="100%" stop-color="#f43f5e" stop-opacity="0"/>
    </radialGradient>
    <filter id="softShadowLevi" x="-10%" y="-10%" width="120%" height="120%">
      <feDropShadow dx="0" dy="4" stdDeviation="3" flood-opacity="0.15"/>
    </filter>
  </defs>

  <!-- Shadow -->
  <ellipse cx="150" cy="375" rx="55" ry="12" fill="#0f172a" opacity="0.12"/>

  <!-- Legs & Shoes -->
  <g id="legs">
    <!-- Left Leg -->
    <rect x="118" y="295" width="24" height="45" rx="10" fill="#fed7aa" stroke="#1e293b" stroke-width="3"/>
    <!-- Left Sock & Shoe -->
    <rect x="116" y="335" width="28" height="12" rx="4" fill="#ffffff" stroke="#1e293b" stroke-width="2.5"/>
    <path d="M 110 347 Q 130 342 146 347 L 146 362 Q 128 365 110 362 Z" fill="#1e3a8a" stroke="#1e293b" stroke-width="3"/>
    <ellipse cx="120" cy="355" rx="6" ry="3" fill="#ffffff"/>

    <!-- Right Leg -->
    <rect x="158" y="295" width="24" height="45" rx="10" fill="#fed7aa" stroke="#1e293b" stroke-width="3"/>
    <!-- Right Sock & Shoe -->
    <rect x="156" y="335" width="28" height="12" rx="4" fill="#ffffff" stroke="#1e293b" stroke-width="2.5"/>
    <path d="M 154 347 Q 170 342 190 347 L 190 362 Q 172 365 154 362 Z" fill="#1e3a8a" stroke="#1e293b" stroke-width="3"/>
    <ellipse cx="180" cy="355" rx="6" ry="3" fill="#ffffff"/>
  </g>

  <!-- Blue Toddler Shorts -->
  <path d="M 105 255 L 195 255 L 190 305 L 155 305 L 150 280 L 145 305 L 110 305 Z" fill="#3b82f6" stroke="#1e293b" stroke-width="3.5" stroke-linejoin="round"/>
  <!-- Shorts pockets / stitching -->
  <path d="M 115 270 Q 125 285 135 270" fill="none" stroke="#2563eb" stroke-width="2"/>
  <path d="M 165 270 Q 175 285 185 270" fill="none" stroke="#2563eb" stroke-width="2"/>

  <!-- Arms -->
  <g id="arms">
    <!-- Left Arm -->
    <path d="M 98 190 Q 75 220 95 245" fill="none" stroke="#fed7aa" stroke-width="22" stroke-linecap="round"/>
    <circle cx="95" cy="245" r="12" fill="#fed7aa" stroke="#1e293b" stroke-width="3"/>

    <!-- Right Arm -->
    <path d="M 202 190 Q 225 215 210 245" fill="none" stroke="#fed7aa" stroke-width="22" stroke-linecap="round"/>
    <circle cx="210" cy="245" r="12" fill="#fed7aa" stroke="#1e293b" stroke-width="3"/>
  </g>

  <!-- Torso & Bold Red Polo Shirt -->
  <g id="torso" filter="url(#softShadowLevi)">
    <path d="M 98 175 Q 85 260 102 265 L 198 265 Q 215 260 202 175 Z" fill="#ef4444" stroke="#1e293b" stroke-width="3.5" stroke-linejoin="round"/>
    <!-- Red Sleeves -->
    <path d="M 98 175 L 82 205 L 108 215 L 115 182 Z" fill="#dc2626" stroke="#1e293b" stroke-width="3"/>
    <path d="M 202 175 L 218 205 L 192 215 L 185 182 Z" fill="#dc2626" stroke="#1e293b" stroke-width="3"/>
    <!-- White Collar & Placket -->
    <path d="M 125 175 L 150 200 L 175 175 Z" fill="#ffffff" stroke="#1e293b" stroke-width="3"/>
    <line x1="150" y1="200" x2="150" y2="230" stroke="#1e293b" stroke-width="3"/>
    <circle cx="150" cy="210" r="2.5" fill="#1e293b"/>
    <circle cx="150" cy="222" r="2.5" fill="#1e293b"/>
  </g>

  <!-- Head Assembly -->
  <g id="head" filter="url(#softShadowLevi)">
    <!-- Ears -->
    <circle cx="85" cy="115" r="14" fill="#fed7aa" stroke="#1e293b" stroke-width="3"/>
    <circle cx="85" cy="115" r="7" fill="#fca5a5" opacity="0.6"/>
    <circle cx="215" cy="115" r="14" fill="#fed7aa" stroke="#1e293b" stroke-width="3"/>
    <circle cx="215" cy="115" r="7" fill="#fca5a5" opacity="0.6"/>

    <!-- Chubby Baby Face Base -->
    <path d="M 95 105 C 80 150 115 175 150 175 C 185 175 220 150 205 105 C 200 65 100 65 95 105 Z" fill="#fed7aa" stroke="#1e293b" stroke-width="3.5"/>

    <!-- Rosy Cheeks -->
    <circle cx="112" cy="132" r="16" fill="url(#leviCheek)"/>
    <circle cx="188" cy="132" r="16" fill="url(#leviCheek)"/>

    <!-- Eyes (Big Sparkling Anime-Preschool Eyes) -->
    <g id="eyes">
      <ellipse cx="125" cy="115" rx="10" ry="12" fill="#1e293b"/>
      <circle cx="122" cy="111" r="4.5" fill="#ffffff"/>
      <circle cx="127" cy="120" r="2" fill="#ffffff"/>
      <ellipse cx="175" cy="115" rx="10" ry="12" fill="#1e293b"/>
      <circle cx="172" cy="111" r="4.5" fill="#ffffff"/>
      <circle cx="177" cy="120" r="2" fill="#ffffff"/>
      <path d="M 115 95 Q 125 90 135 95" fill="none" stroke="#1e293b" stroke-width="3" stroke-linecap="round"/>
      <path d="M 165 95 Q 175 90 185 95" fill="none" stroke="#1e293b" stroke-width="3" stroke-linecap="round"/>
    </g>

    <!-- Button Nose -->
    <ellipse cx="150" cy="125" rx="3.5" ry="2.5" fill="#f87171"/>

    <!-- Sweet Focused Toddler Smile -->
    <path d="M 136 138 Q 150 154 164 138" fill="none" stroke="#1e293b" stroke-width="3.5" stroke-linecap="round"/>
    <path d="M 138 139 Q 150 150 162 139 Z" fill="#fb7185"/>

    <!-- Distinctive Hair: Straight Bangs Fringe Across Forehead (Levi's Signature) -->
    <g id="hair">
      <path d="M 94 95 Q 88 50 150 46 Q 212 50 206 95 C 195 82 175 80 150 80 C 125 80 105 82 94 95 Z" fill="#292524" stroke="#1e293b" stroke-width="3.5" stroke-linejoin="round"/>
      <path d="M 95 86 L 105 98 L 115 86 L 125 98 L 135 86 L 145 98 L 155 86 L 165 98 L 175 86 L 185 98 L 195 86 L 205 90 L 205 78 Q 150 72 95 78 Z" fill="#292524" stroke="#1e293b" stroke-width="2" stroke-linejoin="round"/>
      <path d="M 115 62 Q 150 56 185 62" fill="none" stroke="#57534e" stroke-width="3.5" stroke-linecap="round"/>
    </g>
  </g>
</svg>""",
    "luca": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 300 400" width="100%" height="100%">
  <!-- Luca: Younger Twin Brother (細佬) -->
  <!-- Proportions: 1-2 year old toddler, chubby round cheeks, sunny yellow polo, spiky hair tuft -->
  <defs>
    <radialGradient id="lucaCheek" cx="50%" cy="50%" r="50%">
      <stop offset="0%" stop-color="#f43f5e" stop-opacity="0.35"/>
      <stop offset="100%" stop-color="#f43f5e" stop-opacity="0"/>
    </radialGradient>
    <filter id="softShadow" x="-10%" y="-10%" width="120%" height="120%">
      <feDropShadow dx="0" dy="4" stdDeviation="3" flood-opacity="0.15"/>
    </filter>
  </defs>

  <!-- Shadow -->
  <ellipse cx="150" cy="375" rx="55" ry="12" fill="#0f172a" opacity="0.12"/>

  <!-- Legs & Shoes -->
  <g id="legs">
    <!-- Left Leg -->
    <rect x="118" y="295" width="24" height="45" rx="10" fill="#fed7aa" stroke="#1e293b" stroke-width="3"/>
    <!-- Left Sock & Shoe -->
    <rect x="116" y="335" width="28" height="12" rx="4" fill="#ffffff" stroke="#1e293b" stroke-width="2.5"/>
    <path d="M 110 347 Q 130 342 146 347 L 146 362 Q 128 365 110 362 Z" fill="#3b82f6" stroke="#1e293b" stroke-width="3"/>
    <ellipse cx="120" cy="355" rx="6" ry="3" fill="#ffffff"/>

    <!-- Right Leg -->
    <rect x="158" y="295" width="24" height="45" rx="10" fill="#fed7aa" stroke="#1e293b" stroke-width="3"/>
    <!-- Right Sock & Shoe -->
    <rect x="156" y="335" width="28" height="12" rx="4" fill="#ffffff" stroke="#1e293b" stroke-width="2.5"/>
    <path d="M 154 347 Q 170 342 190 347 L 190 362 Q 172 365 154 362 Z" fill="#3b82f6" stroke="#1e293b" stroke-width="3"/>
    <ellipse cx="180" cy="355" rx="6" ry="3" fill="#ffffff"/>
  </g>

  <!-- Blue Toddler Shorts -->
  <path d="M 105 255 L 195 255 L 190 305 L 155 305 L 150 280 L 145 305 L 110 305 Z" fill="#2563eb" stroke="#1e293b" stroke-width="3.5" stroke-linejoin="round"/>
  <!-- Shorts pockets / stitching -->
  <path d="M 115 270 Q 125 285 135 270" fill="none" stroke="#1d4ed8" stroke-width="2"/>
  <path d="M 165 270 Q 175 285 185 270" fill="none" stroke="#1d4ed8" stroke-width="2"/>

  <!-- Arms -->
  <g id="arms">
    <!-- Left Arm (Gentle wave) -->
    <path d="M 98 190 Q 70 215 80 250" fill="none" stroke="#fed7aa" stroke-width="22" stroke-linecap="round"/>
    <circle cx="80" cy="250" r="12" fill="#fed7aa" stroke="#1e293b" stroke-width="3"/>

    <!-- Right Arm (Raised cheerily) -->
    <path d="M 202 190 Q 230 205 225 240" fill="none" stroke="#fed7aa" stroke-width="22" stroke-linecap="round"/>
    <circle cx="225" cy="240" r="12" fill="#fed7aa" stroke="#1e293b" stroke-width="3"/>
  </g>

  <!-- Torso & Sunny Yellow Polo Shirt -->
  <g id="torso" filter="url(#softShadow)">
    <path d="M 98 175 Q 85 260 102 265 L 198 265 Q 215 260 202 175 Z" fill="#facc15" stroke="#1e293b" stroke-width="3.5" stroke-linejoin="round"/>
    <!-- Yellow Sleeves -->
    <path d="M 98 175 L 82 205 L 108 215 L 115 182 Z" fill="#eab308" stroke="#1e293b" stroke-width="3"/>
    <path d="M 202 175 L 218 205 L 192 215 L 185 182 Z" fill="#eab308" stroke="#1e293b" stroke-width="3"/>
    <!-- Collar & Placket -->
    <path d="M 125 175 L 150 200 L 175 175 Z" fill="#ffffff" stroke="#1e293b" stroke-width="3"/>
    <line x1="150" y1="200" x2="150" y2="230" stroke="#1e293b" stroke-width="3"/>
    <circle cx="150" cy="210" r="2.5" fill="#1e293b"/>
    <circle cx="150" cy="222" r="2.5" fill="#1e293b"/>
  </g>

  <!-- Head Assembly -->
  <g id="head" filter="url(#softShadow)">
    <!-- Ears -->
    <circle cx="85" cy="115" r="14" fill="#fed7aa" stroke="#1e293b" stroke-width="3"/>
    <circle cx="85" cy="115" r="7" fill="#fca5a5" opacity="0.6"/>
    <circle cx="215" cy="115" r="14" fill="#fed7aa" stroke="#1e293b" stroke-width="3"/>
    <circle cx="215" cy="115" r="7" fill="#fca5a5" opacity="0.6"/>

    <!-- Chubby Baby Face Base -->
    <path d="M 95 105 C 80 150 115 175 150 175 C 185 175 220 150 205 105 C 200 65 100 65 95 105 Z" fill="#fed7aa" stroke="#1e293b" stroke-width="3.5"/>

    <!-- Rosy Cheeks -->
    <circle cx="112" cy="132" r="16" fill="url(#lucaCheek)"/>
    <circle cx="188" cy="132" r="16" fill="url(#lucaCheek)"/>

    <!-- Eyes (Big Sparkling Anime-Preschool Eyes) -->
    <g id="eyes">
      <!-- Left Eye -->
      <ellipse cx="125" cy="115" rx="10" ry="12" fill="#1e293b"/>
      <circle cx="122" cy="111" r="4.5" fill="#ffffff"/>
      <circle cx="127" cy="120" r="2" fill="#ffffff"/>
      <!-- Right Eye -->
      <ellipse cx="175" cy="115" rx="10" ry="12" fill="#1e293b"/>
      <circle cx="172" cy="111" r="4.5" fill="#ffffff"/>
      <circle cx="177" cy="120" r="2" fill="#ffffff"/>
      <!-- Soft Eyebrows -->
      <path d="M 115 96 Q 125 90 135 94" fill="none" stroke="#1e293b" stroke-width="3" stroke-linecap="round"/>
      <path d="M 165 94 Q 175 90 185 96" fill="none" stroke="#1e293b" stroke-width="3" stroke-linecap="round"/>
    </g>

    <!-- Cute Button Nose -->
    <ellipse cx="150" cy="125" rx="3.5" ry="2.5" fill="#f87171"/>

    <!-- Joyful Open-Mouth Grin with Tiny Baby Teeth -->
    <path d="M 134 135 Q 150 162 166 135 Q 150 138 134 135 Z" fill="#be123c" stroke="#1e293b" stroke-width="2.5"/>
    <!-- Tiny Front Teeth -->
    <path d="M 144 136 L 144 141 L 156 141 L 156 136 Z" fill="#ffffff"/>
    <!-- Pink Tongue -->
    <path d="M 140 152 Q 150 144 160 152 Q 150 160 140 152 Z" fill="#fb7185"/>

    <!-- Distinctive Hair: Spiky Textured Hair Tuft on Top (Luca's Signature) -->
    <g id="hair">
      <path d="M 94 95 Q 88 55 130 50 Q 138 32 148 24 Q 156 34 162 48 Q 205 52 206 95 C 195 85 180 88 170 82 C 158 75 142 75 130 82 C 120 88 105 85 94 95 Z" fill="#292524" stroke="#1e293b" stroke-width="3.5" stroke-linejoin="round"/>
      <!-- Playful Spikes Detail -->
      <path d="M 142 38 Q 146 16 154 22 Q 158 35 152 46" fill="#292524" stroke="#1e293b" stroke-width="2.5" stroke-linejoin="round"/>
      <path d="M 152 28 Q 162 18 165 28 Q 166 38 160 46" fill="#292524" stroke="#1e293b" stroke-width="2" stroke-linejoin="round"/>
      <!-- Hair Shine Highlights -->
      <path d="M 112 60 Q 130 52 144 56" fill="none" stroke="#57534e" stroke-width="3.5" stroke-linecap="round"/>
      <path d="M 166 56 Q 178 54 190 62" fill="none" stroke="#57534e" stroke-width="3.5" stroke-linecap="round"/>
    </g>
  </g>
</svg>""",

    "dad": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 300 450" width="100%" height="100%">
  <!-- Dad: Chi Shing (爸爸) -->
  <!-- Proportions: Adult father, modern thin black rectangular glasses, neat side-part hair, warm smile, navy tee -->
  <defs>
    <filter id="softShadowDad" x="-10%" y="-10%" width="120%" height="120%">
      <feDropShadow dx="0" dy="4" stdDeviation="3.5" flood-opacity="0.15"/>
    </filter>
  </defs>

  <!-- Ground Shadow -->
  <ellipse cx="150" cy="425" rx="65" ry="14" fill="#0f172a" opacity="0.12"/>

  <!-- Legs & Shoes -->
  <g id="legsDad">
    <!-- Slate Grey Trousers -->
    <path d="M 112 265 L 188 265 L 182 385 L 155 385 L 150 295 L 145 385 L 118 385 Z" fill="#334155" stroke="#0f172a" stroke-width="3.5" stroke-linejoin="round"/>
    <!-- Shoes (Casual White/Grey Sneakers) -->
    <path d="M 108 385 L 142 385 L 145 412 Q 120 415 102 408 Z" fill="#f1f5f9" stroke="#0f172a" stroke-width="3"/>
    <line x1="105" y1="405" x2="145" y2="405" stroke="#94a3b8" stroke-width="2.5"/>
    <path d="M 158 385 L 192 385 L 198 408 Q 180 415 155 412 Z" fill="#f1f5f9" stroke="#0f172a" stroke-width="3"/>
    <line x1="155" y1="405" x2="195" y2="405" stroke="#94a3b8" stroke-width="2.5"/>
  </g>

  <!-- Arms -->
  <g id="armsDad">
    <!-- Left Arm -->
    <path d="M 95 165 Q 75 220 85 270" fill="none" stroke="#fed7aa" stroke-width="26" stroke-linecap="round"/>
    <circle cx="85" cy="270" r="14" fill="#fed7aa" stroke="#0f172a" stroke-width="3"/>
    <!-- Right Arm (Warm welcoming pose) -->
    <path d="M 205 165 Q 225 210 215 260" fill="none" stroke="#fed7aa" stroke-width="26" stroke-linecap="round"/>
    <circle cx="215" cy="260" r="14" fill="#fed7aa" stroke="#0f172a" stroke-width="3"/>
  </g>

  <!-- Torso & Navy T-shirt -->
  <g id="torsoDad" filter="url(#softShadowDad)">
    <path d="M 95 155 Q 88 265 105 275 L 195 275 Q 212 265 205 155 Z" fill="#1e3a8a" stroke="#0f172a" stroke-width="3.5" stroke-linejoin="round"/>
    <!-- Sleeves -->
    <path d="M 95 155 L 75 195 L 105 205 L 115 160 Z" fill="#172554" stroke="#0f172a" stroke-width="3"/>
    <path d="M 205 155 L 225 195 L 195 205 L 185 160 Z" fill="#172554" stroke="#0f172a" stroke-width="3"/>
    <!-- Crew Neckline -->
    <path d="M 132 155 Q 150 170 168 155" fill="none" stroke="#0f172a" stroke-width="3.5"/>
    <path d="M 135 155 Q 150 166 165 155" fill="#fed7aa"/>
  </g>

  <!-- Head Assembly -->
  <g id="headDad" filter="url(#softShadowDad)">
    <!-- Neck -->
    <rect x="135" y="135" width="30" height="25" fill="#fed7aa" stroke="#0f172a" stroke-width="3"/>

    <!-- Ears -->
    <circle cx="95" cy="98" r="14" fill="#fed7aa" stroke="#0f172a" stroke-width="3"/>
    <circle cx="205" cy="98" r="14" fill="#fed7aa" stroke="#0f172a" stroke-width="3"/>

    <!-- Face Base -->
    <path d="M 102 85 C 96 130 115 145 150 145 C 185 145 204 130 198 85 C 192 45 108 45 102 85 Z" fill="#fed7aa" stroke="#0f172a" stroke-width="3.5"/>

    <!-- Subtle Stubble / Beard Shadow -->
    <path d="M 125 128 Q 150 142 175 128 Q 150 145 125 128 Z" fill="#e2e8f0" opacity="0.4"/>

    <!-- Eyes Behind Glasses -->
    <ellipse cx="128" cy="95" rx="7" ry="8" fill="#0f172a"/>
    <circle cx="126" cy="92" r="3" fill="#ffffff"/>
    <ellipse cx="172" cy="95" rx="7" ry="8" fill="#0f172a"/>
    <circle cx="170" cy="92" r="3" fill="#ffffff"/>

    <!-- Modern Thin Black Rectangular Eyeglasses (Dad's Signature!) -->
    <!-- Left Lens Frame -->
    <rect x="112" y="82" width="32" height="26" rx="6" fill="none" stroke="#0f172a" stroke-width="3.5"/>
    <!-- Right Lens Frame -->
    <rect x="156" y="82" width="32" height="26" rx="6" fill="none" stroke="#0f172a" stroke-width="3.5"/>
    <!-- Glasses Bridge -->
    <line x1="144" y1="92" x2="156" y2="92" stroke="#0f172a" stroke-width="3.5"/>
    <!-- Glasses Temples to Ears -->
    <line x1="112" y1="90" x2="98" y2="92" stroke="#0f172a" stroke-width="3"/>
    <line x1="188" y1="90" x2="202" y2="92" stroke="#0f172a" stroke-width="3"/>

    <!-- Eyebrows -->
    <path d="M 114 76 Q 128 72 142 76" fill="none" stroke="#0f172a" stroke-width="3.5" stroke-linecap="round"/>
    <path d="M 158 76 Q 172 72 186 76" fill="none" stroke="#0f172a" stroke-width="3.5" stroke-linecap="round"/>

    <!-- Nose -->
    <path d="M 150 96 L 148 110 L 154 110" fill="none" stroke="#0f172a" stroke-width="2.5" stroke-linecap="round"/>

    <!-- Warm Encouraging Smile -->
    <path d="M 134 122 Q 150 135 166 122" fill="none" stroke="#0f172a" stroke-width="3.5" stroke-linecap="round"/>
    <path d="M 135 123 Q 150 132 165 123 Z" fill="#ffffff"/>

    <!-- Hair: Short Neat Side-Swept Black Hair (Side Part) -->
    <path d="M 98 82 Q 95 38 140 35 Q 185 32 202 70 Q 205 88 198 92 C 190 75 178 72 155 70 C 130 68 110 75 98 82 Z" fill="#1c1917" stroke="#0f172a" stroke-width="3.5" stroke-linejoin="round"/>
    <!-- Side Part Sweep Details -->
    <path d="M 132 38 Q 148 55 175 60" fill="none" stroke="#44403c" stroke-width="3" stroke-linecap="round"/>
    <path d="M 115 48 Q 130 62 148 65" fill="none" stroke="#44403c" stroke-width="2.5" stroke-linecap="round"/>
  </g>
</svg>""",

    "mom": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 300 450" width="100%" height="100%">
  <!-- Mom (媽媽) -->
  <!-- Proportions: Warm feminine mother, radiant smile, side ponytail with bangs, cozy pink knit sweater -->
  <defs>
    <filter id="softShadowMom" x="-10%" y="-10%" width="120%" height="120%">
      <feDropShadow dx="0" dy="4" stdDeviation="3.5" flood-opacity="0.15"/>
    </filter>
  </defs>

  <!-- Shadow -->
  <ellipse cx="150" cy="425" rx="60" ry="13" fill="#0f172a" opacity="0.12"/>

  <!-- Legs & Shoes -->
  <g id="legsMom">
    <!-- Cream / Dark Trousers -->
    <path d="M 116 270 L 184 270 L 180 385 L 155 385 L 150 295 L 145 385 L 120 385 Z" fill="#475569" stroke="#0f172a" stroke-width="3.5" stroke-linejoin="round"/>
    <!-- Cozy Slip-on Flats -->
    <path d="M 112 385 Q 140 380 142 410 Q 120 412 110 405 Z" fill="#fb7185" stroke="#0f172a" stroke-width="3"/>
    <path d="M 158 385 Q 186 380 188 410 Q 170 412 156 405 Z" fill="#fb7185" stroke="#0f172a" stroke-width="3"/>
  </g>

  <!-- Arms -->
  <g id="armsMom">
    <!-- Left Arm -->
    <path d="M 100 165 Q 80 215 90 265" fill="none" stroke="#fed7aa" stroke-width="24" stroke-linecap="round"/>
    <circle cx="90" cy="265" r="13" fill="#fed7aa" stroke="#0f172a" stroke-width="3"/>
    <!-- Right Arm (Gentle hugging / welcoming pose) -->
    <path d="M 200 165 Q 220 215 210 265" fill="none" stroke="#fed7aa" stroke-width="24" stroke-linecap="round"/>
    <circle cx="210" cy="265" r="13" fill="#fed7aa" stroke="#0f172a" stroke-width="3"/>
  </g>

  <!-- Torso & Cozy Warm Pink Knit Sweater -->
  <g id="torsoMom" filter="url(#softShadowMom)">
    <path d="M 100 155 Q 90 265 108 275 L 192 275 Q 210 265 200 155 Z" fill="#f472b6" stroke="#0f172a" stroke-width="3.5" stroke-linejoin="round"/>
    <!-- Knit texture lines -->
    <line x1="120" y1="180" x2="120" y2="265" stroke="#ec4899" stroke-width="2" stroke-dasharray="4 4"/>
    <line x1="140" y1="175" x2="140" y2="270" stroke="#ec4899" stroke-width="2" stroke-dasharray="4 4"/>
    <line x1="160" y1="175" x2="160" y2="270" stroke="#ec4899" stroke-width="2" stroke-dasharray="4 4"/>
    <line x1="180" y1="180" x2="180" y2="265" stroke="#ec4899" stroke-width="2" stroke-dasharray="4 4"/>
    <!-- Cozy Mock Turtleneck Collar -->
    <rect x="125" y="135" width="50" height="25" rx="8" fill="#db2777" stroke="#0f172a" stroke-width="3"/>
  </g>

  <!-- Head Assembly -->
  <g id="headMom" filter="url(#softShadowMom)">
    <!-- Side Ponytail Hair Behind Head -->
    <path d="M 195 85 Q 240 95 245 145 Q 235 170 210 160 Q 225 130 195 105 Z" fill="#1c1917" stroke="#0f172a" stroke-width="3.5" stroke-linejoin="round"/>
    <ellipse cx="205" cy="100" rx="8" ry="6" fill="#f43f5e"/> <!-- Cute Hair Tie -->

    <!-- Ears -->
    <circle cx="102" cy="98" r="12" fill="#fed7aa" stroke="#0f172a" stroke-width="3"/>
    <circle cx="198" cy="98" r="12" fill="#fed7aa" stroke="#0f172a" stroke-width="3"/>

    <!-- Face Base -->
    <path d="M 106 85 C 102 128 118 142 150 142 C 182 142 198 128 194 85 C 190 48 110 48 106 85 Z" fill="#fed7aa" stroke="#0f172a" stroke-width="3.5"/>

    <!-- Cheeks Blush -->
    <circle cx="118" cy="115" r="12" fill="#f43f5e" opacity="0.3"/>
    <circle cx="182" cy="115" r="12" fill="#f43f5e" opacity="0.3"/>

    <!-- Eyes (Gentle Almond Eyes with Winged Eyeliner) -->
    <path d="M 118 95 Q 128 90 138 95" fill="none" stroke="#0f172a" stroke-width="3.5"/>
    <line x1="138" y1="95" x2="143" y2="92" stroke="#0f172a" stroke-width="3.5" stroke-linecap="round"/>
    <ellipse cx="128" cy="98" rx="6.5" ry="7.5" fill="#0f172a"/>
    <circle cx="126" cy="95" r="3" fill="#ffffff"/>

    <path d="M 162 95 Q 172 90 182 95" fill="none" stroke="#0f172a" stroke-width="3.5"/>
    <line x1="182" y1="95" x2="187" y2="92" stroke="#0f172a" stroke-width="3.5" stroke-linecap="round"/>
    <ellipse cx="172" cy="98" rx="6.5" ry="7.5" fill="#0f172a"/>
    <circle cx="170" cy="95" r="3" fill="#ffffff"/>

    <!-- Eyebrows -->
    <path d="M 118 84 Q 128 80 138 84" fill="none" stroke="#1c1917" stroke-width="2.5" stroke-linecap="round"/>
    <path d="M 162 84 Q 172 80 182 84" fill="none" stroke="#1c1917" stroke-width="2.5" stroke-linecap="round"/>

    <!-- Small Nose -->
    <circle cx="150" cy="106" r="2.5" fill="#f87171"/>

    <!-- Radiant Sunny Smile -->
    <path d="M 136 118 Q 150 134 164 118" fill="none" stroke="#0f172a" stroke-width="3" stroke-linecap="round"/>
    <path d="M 137 119 Q 150 132 163 119 Z" fill="#ffffff"/>

    <!-- Hair: Bangs and Side Flow -->
    <g id="hairMom">
      <path d="M 104 80 Q 100 42 145 38 Q 190 38 196 80 C 185 70 170 65 150 66 C 130 65 115 70 104 80 Z" fill="#1c1917" stroke="#0f172a" stroke-width="3.5"/>
      <!-- Soft Front Fringe Bangs -->
      <path d="M 112 68 Q 128 85 142 74 Q 155 86 168 70 Q 182 84 190 75" fill="none" stroke="#0f172a" stroke-width="3"/>
    </g>
  </g>
</svg>""",

    "dog_spitz": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 320 300" width="100%" height="100%">
  <!-- Family Dog: Pure White Fluffy Japanese Spitz / American Eskimo (小白狗) -->
  <!-- Characteristics: Cloud-like voluminous white fur, alert prick ears, black button nose, holds white ball, plume tail curled over back -->
  <defs>
    <filter id="fluffyShadow" x="-10%" y="-10%" width="120%" height="120%">
      <feDropShadow dx="0" dy="4" stdDeviation="3" flood-opacity="0.12"/>
    </filter>
  </defs>

  <!-- Ground Shadow -->
  <ellipse cx="160" cy="275" rx="75" ry="14" fill="#0f172a" opacity="0.12"/>

  <!-- Paws & Legs -->
  <g id="dogLegs">
    <rect x="100" y="215" width="20" height="50" rx="10" fill="#ffffff" stroke="#cbd5e1" stroke-width="3"/>
    <rect x="135" y="215" width="20" height="50" rx="10" fill="#ffffff" stroke="#cbd5e1" stroke-width="3"/>
    <rect x="175" y="215" width="20" height="50" rx="10" fill="#ffffff" stroke="#cbd5e1" stroke-width="3"/>
    <rect x="210" y="215" width="20" height="50" rx="10" fill="#ffffff" stroke="#cbd5e1" stroke-width="3"/>
  </g>

  <!-- Fluffy Cloud Body -->
  <g id="dogBody" filter="url(#fluffyShadow)">
    <path d="M 90 190 Q 75 145 110 130 Q 140 125 180 130 Q 220 140 235 180 Q 245 225 210 235 Q 170 245 120 235 Q 85 225 90 190 Z" fill="#ffffff" stroke="#cbd5e1" stroke-width="3.5"/>
    <!-- Fluff Tufts Outline Accents -->
    <path d="M 85 170 Q 75 180 85 190 Q 75 200 88 210" fill="none" stroke="#cbd5e1" stroke-width="2.5"/>
    <path d="M 230 160 Q 242 175 232 190 Q 242 205 230 215" fill="none" stroke="#cbd5e1" stroke-width="2.5"/>
  </g>

  <!-- Plume Fluffy Tail Curled Over Back (Wagging) -->
  <g id="dogTail" filter="url(#fluffyShadow)">
    <path d="M 220 160 Q 255 120 250 85 Q 235 65 215 80 Q 195 95 210 130 Z" fill="#ffffff" stroke="#cbd5e1" stroke-width="3"/>
    <path d="M 238 75 Q 255 85 248 105" fill="none" stroke="#cbd5e1" stroke-width="2"/>
  </g>

  <!-- Fluffy Chest Ruff -->
  <path d="M 100 155 Q 70 185 105 210 Q 125 225 145 215 Q 120 175 100 155 Z" fill="#ffffff" stroke="#cbd5e1" stroke-width="3"/>

  <!-- Head & Facial Assembly -->
  <g id="dogHead" filter="url(#fluffyShadow)">
    <!-- Fluffy Head Mane -->
    <ellipse cx="110" cy="120" rx="42" ry="40" fill="#ffffff" stroke="#cbd5e1" stroke-width="3.5"/>

    <!-- Alert Prick Ears (Small Triangular) -->
    <!-- Left Ear -->
    <path d="M 82 95 L 88 55 L 108 85 Z" fill="#ffffff" stroke="#cbd5e1" stroke-width="3" stroke-linejoin="round"/>
    <path d="M 86 90 L 90 65 L 102 85 Z" fill="#fecdd3"/> <!-- Pink Ear Interior -->
    <!-- Right Ear -->
    <path d="M 115 85 L 132 55 L 140 95 Z" fill="#ffffff" stroke="#cbd5e1" stroke-width="3" stroke-linejoin="round"/>
    <path d="M 120 85 L 130 65 L 135 90 Z" fill="#fecdd3"/> <!-- Pink Ear Interior -->

    <!-- Snout / Muzzle -->
    <ellipse cx="88" cy="135" rx="20" ry="16" fill="#ffffff" stroke="#cbd5e1" stroke-width="2.5"/>

    <!-- Shiny Black Eyes with Sparkling Highlight -->
    <ellipse cx="92" cy="112" rx="6.5" ry="7.5" fill="#0f172a"/>
    <circle cx="90" cy="109" r="2.5" fill="#ffffff"/>

    <ellipse cx="125" cy="114" rx="6.5" ry="7.5" fill="#0f172a"/>
    <circle cx="123" cy="111" r="2.5" fill="#ffffff"/>

    <!-- Black Button Nose -->
    <ellipse cx="76" cy="128" rx="5" ry="4" fill="#0f172a"/>

    <!-- Open Doggy Smile holding White Ball! -->
    <path d="M 76 136 Q 88 152 102 138" fill="none" stroke="#0f172a" stroke-width="3"/>
    
    <!-- Signature White Tennis Ball / Toy Held in Mouth (from photo!) -->
    <circle cx="82" cy="144" r="14" fill="#f8fafc" stroke="#94a3b8" stroke-width="2.5"/>
    <path d="M 72 140 Q 82 148 92 140" fill="none" stroke="#cbd5e1" stroke-width="2"/>

    <!-- Red Collar with Shiny Golden Bell -->
    <path d="M 115 155 Q 135 170 152 155" fill="none" stroke="#ef4444" stroke-width="7" stroke-linecap="round"/>
    <circle cx="136" cy="168" r="6.5" fill="#facc15" stroke="#ca8a04" stroke-width="2"/>
    <circle cx="136" cy="169" r="1.5" fill="#78350f"/>
  </g>
</svg>"""
}

# Write out SVGs to assets/characters/
for char_id, svg_code in CHARACTERS_SVG.items():
    path = f"assets/characters/{char_id}.svg"
    with open(path, "w", encoding="utf-8") as f:
        f.write(svg_code.strip())
    print(f"Generated {path}")

print("Vector character assets generated successfully!")
