# scripts/build_showcase_html.py
import os
import shutil

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-HK">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>粵語幼兒動畫：角色設計審閱中心 (Character Design Review)</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+TC:wght@400;500;700;900&display=swap');
    body { font-family: 'Noto Sans TC', system-ui, -apple-system, sans-serif; }
    .card-hover:hover {
      transform: translateY(-3px);
      box-shadow: 0 12px 24px -8px rgba(0, 0, 0, 0.12);
      transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
    }
  </style>
</head>
<body class="bg-slate-100 text-slate-800 antialiased p-4 md:p-8">
  <div class="max-w-6xl mx-auto space-y-8">

    <!-- Header Banner -->
    <div class="bg-gradient-to-r from-blue-700 via-indigo-600 to-purple-600 text-white p-6 rounded-2xl shadow-md">
      <div class="flex flex-col md:flex-row justify-between md:items-center gap-4">
        <div>
          <span class="inline-block px-3 py-1 bg-white/20 backdrop-blur text-white text-xs font-bold rounded-full mb-2">
            🎨 第一階段：角色造型審閱 (Pre-Animation Approval)
          </span>
          <h1 class="text-2xl md:text-3xl font-black tracking-tight">
            《哥哥細佬嘅開心一日》角色造型審查展示
          </h1>
          <p class="text-sm text-blue-100 mt-1 max-w-2xl">
            根據您上載的家庭真實照片精心繪製的 2D 幼兒動畫角色。請仔細檢查各家庭成員的卡通造型，確認滿意後我們即刻開展 2.5 分鐘全動態影片製作！
          </p>
        </div>
        <div class="flex flex-col sm:flex-row items-start sm:items-center gap-2 shrink-0">
          <div class="bg-emerald-500 text-white font-bold text-xs px-3 py-2 rounded-xl shadow flex items-center gap-1.5">
            <span class="w-2.5 h-2.5 bg-white rounded-full animate-ping"></span>
            8組家庭角色就緒
          </div>
        </div>
      </div>
    </div>

    <!-- Section 1: Side-by-Side Character Comparison Gallery -->
    <div class="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm space-y-6">
      <div class="border-b border-slate-200 pb-4 flex flex-col sm:flex-row justify-between sm:items-center gap-2">
        <div>
          <h2 class="text-xl md:text-2xl font-black text-slate-900 flex items-center gap-2">
            <span>👨‍👩‍👦‍👦</span> 1. 家庭成員真人照片 vs 2D 卡通造型對比
          </h2>
          <p class="text-sm text-slate-500 mt-0.5">
            結合《Bluey》及《Miss Ka Foo》幼兒插畫風格，精準還原每位家庭成員的核心面貌特徵。
          </p>
        </div>
        <span class="text-xs font-semibold px-3 py-1 bg-blue-50 text-blue-700 border border-blue-200 rounded-full w-fit">
          可進行骨骼關節動畫 (Rigged Vectors)
        </span>
      </div>

      <!-- Character Pairs Grid -->
      <div class="grid grid-cols-1 gap-8">

        <!-- Levi (Older Twin Brother / 哥哥) -->
        <div class="border border-slate-200 rounded-2xl p-5 bg-slate-50 card-hover">
          <div class="flex flex-wrap items-center justify-between gap-2 mb-4 pb-3 border-b border-slate-200">
            <div class="flex items-center gap-2.5">
              <span class="bg-rose-600 text-white font-bold text-xs px-2.5 py-1 rounded-lg shadow-sm">雙胞胎大佬</span>
              <h3 class="font-black text-xl text-slate-900">Levi 哥哥 (go4-go1)</h3>
              <span class="text-xs bg-rose-100 text-rose-800 font-semibold px-2 py-0.5 rounded-full">紅色 Polo 衫 ‧ 齊蔭直瀏海</span>
            </div>
            <span class="text-xs text-slate-500 font-medium">主要特徵：乖巧專注、圓滾粉頰、標誌齊瀏海</span>
          </div>

          <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
            <!-- Real Photo -->
            <div class="space-y-2">
              <div class="text-xs font-bold text-slate-600 flex items-center gap-1">
                <span>📸</span> 真人照片參照
              </div>
              <div class="h-72 rounded-xl overflow-hidden bg-slate-200 border border-slate-300 shadow-inner flex items-center justify-center">
                <img src="/assets/raw_photos/levi_older_brother/20260701_104200_7d434ade.jpg" class="w-full h-full object-cover object-center" alt="Levi Real Photo">
              </div>
              <p class="text-xs text-slate-600 leading-relaxed">圓潤臉蛋、順貼前額的整齊直瀏海、清澈專注眼神、亮紅色上衣。</p>
            </div>

            <!-- AI 2D Concept Art -->
            <div class="space-y-2">
              <div class="text-xs font-bold text-indigo-600 flex items-center gap-1">
                <span>🎨</span> 2D 概念插畫 (AI Concept)
              </div>
              <div class="h-72 rounded-xl overflow-hidden bg-white border-2 border-indigo-200 shadow-inner flex items-center justify-center p-2">
                <img src="/assets/characters/levi_cartoon.jpg" class="max-h-full object-contain rounded-lg" alt="Levi Concept Art">
              </div>
              <p class="text-xs text-indigo-800 leading-relaxed">暖色調水彩厚塗風格，大眼睛與招牌齊蔭，粉嫩雙頰。</p>
            </div>

            <!-- Rigged Vector Model -->
            <div class="space-y-2">
              <div class="text-xs font-bold text-rose-600 flex items-center gap-1">
                <span>⚡</span> 動畫骨骼矢量模型 (Rigged Vector SVG)
              </div>
              <div class="h-72 rounded-xl overflow-hidden bg-white border-2 border-rose-300 shadow-inner flex items-center justify-center p-3">
                <img src="/assets/characters/levi.svg" class="max-h-full object-contain" alt="Levi Vector">
              </div>
              <p class="text-xs text-rose-800 leading-relaxed">獨立圖層分組（眼睛、嘴型、四肢、軀幹），支援眨眼、行路及踩單車動作！</p>
            </div>
          </div>
        </div>

        <!-- Luca (Younger Twin Brother / 細佬) -->
        <div class="border border-slate-200 rounded-2xl p-5 bg-slate-50 card-hover">
          <div class="flex flex-wrap items-center justify-between gap-2 mb-4 pb-3 border-b border-slate-200">
            <div class="flex items-center gap-2.5">
              <span class="bg-amber-500 text-white font-bold text-xs px-2.5 py-1 rounded-lg shadow-sm">雙胞胎細佬</span>
              <h3 class="font-black text-xl text-slate-900">Luca 細佬 (sai3-lou2)</h3>
              <span class="text-xs bg-amber-100 text-amber-800 font-semibold px-2 py-0.5 rounded-full">陽光黃色 Polo 衫 ‧ 頭頂呆毛微翹</span>
            </div>
            <span class="text-xs text-slate-500 font-medium">主要特徵：活潑開朗、愛笑露乳齒、頭頂微翹碎髮</span>
          </div>

          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <!-- Real Photo -->
            <div class="space-y-2">
              <div class="text-xs font-bold text-slate-600 flex items-center gap-1">
                <span>📸</span> 真人照片參照
              </div>
              <div class="h-72 rounded-xl overflow-hidden bg-slate-200 border border-slate-300 shadow-inner flex items-center justify-center">
                <img src="/assets/raw_photos/luca_younger_brother/PXL_20260805_022850458.jpg" class="w-full h-full object-cover object-top" alt="Luca Real Photo">
              </div>
              <p class="text-xs text-slate-600 leading-relaxed">活潑好動、開懷燦爛笑容露小牙齒、頭頂自然微翹的呆毛、亮黃色休閒上衣。</p>
            </div>

            <!-- Rigged Vector Model -->
            <div class="space-y-2">
              <div class="text-xs font-bold text-amber-600 flex items-center gap-1">
                <span>⚡</span> 動畫骨骼矢量模型 (Rigged Vector SVG)
              </div>
              <div class="h-72 rounded-xl overflow-hidden bg-white border-2 border-amber-300 shadow-inner flex items-center justify-center p-3">
                <img src="/assets/characters/luca.svg" class="max-h-full object-contain" alt="Luca Vector">
              </div>
              <p class="text-xs text-amber-800 leading-relaxed">招牌開懷笑臉與小乳齒、頭頂立體碎髮、活潑張手姿勢，完整支援對嘴與跳躍動畫。</p>
            </div>
          </div>
        </div>

        <!-- Dad (Chi Shing / 爸爸) -->
        <div class="border border-slate-200 rounded-2xl p-5 bg-slate-50 card-hover">
          <div class="flex flex-wrap items-center justify-between gap-2 mb-4 pb-3 border-b border-slate-200">
            <div class="flex items-center gap-2.5">
              <span class="bg-blue-700 text-white font-bold text-xs px-2.5 py-1 rounded-lg shadow-sm">旁白敘事者</span>
              <h3 class="font-black text-xl text-slate-900">Chi Shing 爸爸 (baa4-baa1)</h3>
              <span class="text-xs bg-blue-100 text-blue-800 font-semibold px-2 py-0.5 rounded-full">深藍 T-shirt ‧ 現代黑框眼鏡 ‧ 慈祥微笑</span>
            </div>
            <span class="text-xs text-slate-500 font-medium">全劇旁白配音靈魂人物，引導小朋友認知探索</span>
          </div>

          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <!-- Real Photo -->
            <div class="space-y-2">
              <div class="text-xs font-bold text-slate-600 flex items-center gap-1">
                <span>📸</span> 真人照片參照
              </div>
              <div class="h-72 rounded-xl overflow-hidden bg-slate-200 border border-slate-300 shadow-inner flex items-center justify-center">
                <img src="/assets/raw_photos/dad/PXL_20260604_192934949.MP.jpg" class="w-full h-full object-cover object-top" alt="Dad Real Photo">
              </div>
              <p class="text-xs text-slate-600 leading-relaxed">親切溫和的父親形象、極具辨識度的簡約黑框眼鏡、俐落旁分短髮、溫暖笑意。</p>
            </div>

            <!-- Rigged Vector Model -->
            <div class="space-y-2">
              <div class="text-xs font-bold text-blue-700 flex items-center gap-1">
                <span>⚡</span> 動畫骨骼矢量模型 (Rigged Vector SVG)
              </div>
              <div class="h-72 rounded-xl overflow-hidden bg-white border-2 border-blue-300 shadow-inner flex items-center justify-center p-3">
                <img src="/assets/characters/dad.svg" class="max-h-full object-contain" alt="Dad Vector">
              </div>
              <p class="text-xs text-blue-800 leading-relaxed">親切黑框眼鏡、深藍暖色棉 T、溫暖張手牽抱動作，與您的真人粵語音軌精準口型同步。</p>
            </div>
          </div>
        </div>

        <!-- Mom (媽媽) -->
        <div class="border border-slate-200 rounded-2xl p-5 bg-slate-50 card-hover">
          <div class="flex flex-wrap items-center justify-between gap-2 mb-4 pb-3 border-b border-slate-200">
            <div class="flex items-center gap-2.5">
              <span class="bg-pink-600 text-white font-bold text-xs px-2.5 py-1 rounded-lg shadow-sm">溫馨擁抱</span>
              <h3 class="font-black text-xl text-slate-900">媽媽 (maa4-maa1)</h3>
              <span class="text-xs bg-pink-100 text-pink-800 font-semibold px-2 py-0.5 rounded-full">粉紅溫暖高領毛衣 ‧ 側綁髮側瀏海</span>
            </div>
            <span class="text-xs text-slate-500 font-medium">於出門前給予雙胞胎溫暖 Hug 與支持</span>
          </div>

          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <!-- Real Photo -->
            <div class="space-y-2">
              <div class="text-xs font-bold text-slate-600 flex items-center gap-1">
                <span>📸</span> 真人照片參照
              </div>
              <div class="h-72 rounded-xl overflow-hidden bg-slate-200 border border-slate-300 shadow-inner flex items-center justify-center">
                <img src="/assets/raw_photos/mom/PXL_20260120_021418032.MP.jpg" class="w-full h-full object-cover object-top" alt="Mom Real Photo">
              </div>
              <p class="text-xs text-slate-600 leading-relaxed">溫婉笑容、清秀靈動眼神、柔和側綁髮與空氣瀏海、粉暖色系穿搭。</p>
            </div>

            <!-- Rigged Vector Model -->
            <div class="space-y-2">
              <div class="text-xs font-bold text-pink-600 flex items-center gap-1">
                <span>⚡</span> 動畫骨骼矢量模型 (Rigged Vector SVG)
              </div>
              <div class="h-72 rounded-xl overflow-hidden bg-white border-2 border-pink-300 shadow-inner flex items-center justify-center p-3">
                <img src="/assets/characters/mom.svg" class="max-h-full object-contain" alt="Mom Vector">
              </div>
              <p class="text-xs text-pink-800 leading-relaxed">柔和粉系高領毛衣、優雅側馬尾、微笑彎眉，為雙胞胎送上擁抱鼓勵。</p>
            </div>
          </div>
        </div>

        <!-- Dog (White Spitz / 小白狗) -->
        <div class="border border-slate-200 rounded-2xl p-5 bg-slate-50 card-hover">
          <div class="flex flex-wrap items-center justify-between gap-2 mb-4 pb-3 border-b border-slate-200">
            <div class="flex items-center gap-2.5">
              <span class="bg-emerald-600 text-white font-bold text-xs px-2.5 py-1 rounded-lg shadow-sm">毛孩成員</span>
              <h3 class="font-black text-xl text-slate-900">純白銀狐 Spitz 小白狗 (siu2-baak6-gau2)</h3>
              <span class="text-xs bg-emerald-100 text-emerald-800 font-semibold px-2 py-0.5 rounded-full">雪白蓬鬆棉花身軀 ‧ 標誌口咬白波 ‧ 警覺立耳</span>
            </div>
            <span class="text-xs text-slate-500 font-medium">糾正先前柴犬設定：完全依據照片還原純白日本銀狐犬！</span>
          </div>

          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <!-- Real Photo -->
            <div class="space-y-2">
              <div class="text-xs font-bold text-slate-600 flex items-center gap-1">
                <span>📸</span> 真人照片參照
              </div>
              <div class="h-72 rounded-xl overflow-hidden bg-slate-200 border border-slate-300 shadow-inner flex items-center justify-center">
                <img src="/assets/raw_photos/dog/IMG_0719.JPG" class="w-full h-full object-cover object-center" alt="Dog Real Photo">
              </div>
              <p class="text-xs text-slate-600 leading-relaxed">雲朵般雪白厚實毛髮、黑色鈕扣鼻、精神直立尖耳、最鐘意口咬白色小球！</p>
            </div>

            <!-- Rigged Vector Model -->
            <div class="space-y-2">
              <div class="text-xs font-bold text-emerald-600 flex items-center gap-1">
                <span>⚡</span> 動畫骨骼矢量模型 (Rigged Vector SVG)
              </div>
              <div class="h-72 rounded-xl overflow-hidden bg-white border-2 border-emerald-300 shadow-inner flex items-center justify-center p-3">
                <img src="/assets/characters/dog_spitz.svg" class="max-h-full object-contain" alt="Dog Vector">
              </div>
              <p class="text-xs text-emerald-800 leading-relaxed">蓬鬆雲朵毛、紅色頸圈配小金鈴鐺、口咬最愛的白色網球、捲翹尾巴支援搖尾動畫！</p>
            </div>
          </div>
        </div>

        <!-- Grandparents Paternal (爺爺 & 嫲嫲) -->
        <div class="border border-slate-200 rounded-2xl p-5 bg-slate-50 card-hover">
          <div class="flex flex-wrap items-center justify-between gap-2 mb-4 pb-3 border-b border-slate-200">
            <div class="flex items-center gap-2.5">
              <span class="bg-purple-600 text-white font-bold text-xs px-2.5 py-1 rounded-lg shadow-sm">父系長輩</span>
              <h3 class="font-black text-xl text-slate-900">爺爺 & 嫲嫲 (je4-je2 & maa4-maa4)</h3>
              <span class="text-xs bg-purple-100 text-purple-800 font-semibold px-2 py-0.5 rounded-full">格紋 Polo 衫 ‧ 金絲眼鏡 ‧ 慈祥短捲髮</span>
            </div>
            <span class="text-xs text-slate-500 font-medium">於家中及公園長凳向 Levi 與 Luca 揮手讚賞</span>
          </div>

          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <!-- Real Photo -->
            <div class="space-y-2">
              <div class="text-xs font-bold text-slate-600 flex items-center gap-1">
                <span>📸</span> 真人照片參照
              </div>
              <div class="h-72 rounded-xl overflow-hidden bg-slate-200 border border-slate-300 shadow-inner flex items-center justify-center">
                <img src="/assets/raw_photos/grandparents_paternal_withtwins/PXL_20260511_031103919.MP.jpg" class="w-full h-full object-cover object-top" alt="Paternal Grandparents Real Photo">
              </div>
              <p class="text-xs text-slate-600 leading-relaxed">爺爺穿著斯文格紋領衫配金屬框眼鏡；嫲嫲留有整齊短捲髮與金屬橢圓鏡框，慈祥抱住雙胞胎。</p>
            </div>

            <!-- Rigged Vector Model -->
            <div class="space-y-2">
              <div class="text-xs font-bold text-purple-600 flex items-center gap-1">
                <span>⚡</span> 動畫骨骼矢量模型 (Rigged Vector SVG)
              </div>
              <div class="h-72 rounded-xl overflow-hidden bg-white border-2 border-purple-300 shadow-inner flex items-center justify-center p-3">
                <img src="/assets/characters/grandparents_paternal.svg" class="max-h-full object-contain" alt="Grandparents Paternal Vector">
              </div>
              <p class="text-xs text-purple-800 leading-relaxed">雙人慈祥長輩模型，神態和藹，配備標準向小朋友鼓掌揮手的動作節點。</p>
            </div>
          </div>
        </div>

        <!-- Grandparents Maternal (公公 & 婆婆) -->
        <div class="border border-slate-200 rounded-2xl p-5 bg-slate-50 card-hover">
          <div class="flex flex-wrap items-center justify-between gap-2 mb-4 pb-3 border-b border-slate-200">
            <div class="flex items-center gap-2.5">
              <span class="bg-teal-600 text-white font-bold text-xs px-2.5 py-1 rounded-lg shadow-sm">母系長輩</span>
              <h3 class="font-black text-xl text-slate-900">公公 & 婆婆 (gung1-gung1 & po4-po2)</h3>
              <span class="text-xs bg-teal-100 text-teal-800 font-semibold px-2 py-0.5 rounded-full">俐落平頭 ‧ 翡翠玉鐲 ‧ 精靈短髮</span>
            </div>
            <span class="text-xs text-slate-500 font-medium">溫暖陪伴雙胞胎戶外散步探索</span>
          </div>

          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <!-- Real Photo -->
            <div class="space-y-2">
              <div class="text-xs font-bold text-slate-600 flex items-center gap-1">
                <span>📸</span> 真人照片參照
              </div>
              <div class="h-72 rounded-xl overflow-hidden bg-slate-200 border border-slate-300 shadow-inner flex items-center justify-center">
                <img src="/assets/raw_photos/grandparents_maternal_withtwins/ff11258a2i78a1a7714b4622ddb2686a.jpg" class="w-full h-full object-cover object-top" alt="Maternal Grandparents Real Photo">
              </div>
              <p class="text-xs text-slate-600 leading-relaxed">公公留有俐落清爽平頭與休閒白色上衣；婆婆神采奕奕、精靈瀏海短髮配手腕溫潤玉鐲。</p>
            </div>

            <!-- Rigged Vector Model -->
            <div class="space-y-2">
              <div class="text-xs font-bold text-teal-600 flex items-center gap-1">
                <span>⚡</span> 動畫骨骼矢量模型 (Rigged Vector SVG)
              </div>
              <div class="h-72 rounded-xl overflow-hidden bg-white border-2 border-teal-300 shadow-inner flex items-center justify-center p-3">
                <img src="/assets/characters/grandparents_maternal.svg" class="max-h-full object-contain" alt="Grandparents Maternal Vector">
              </div>
              <p class="text-xs text-teal-800 leading-relaxed">還原清爽平頭與玉鐲飾物，面帶燦爛笑容，準備在公園給予兩兄弟驚喜！</p>
            </div>
          </div>
        </div>

        <!-- Aunt & Cousins (姑媽, 表哥 Ryan & 表弟) -->
        <div class="border border-slate-200 rounded-2xl p-5 bg-slate-50 card-hover">
          <div class="flex flex-wrap items-center justify-between gap-2 mb-4 pb-3 border-b border-slate-200">
            <div class="flex items-center gap-2.5">
              <span class="bg-orange-500 text-white font-bold text-xs px-2.5 py-1 rounded-lg shadow-sm">同輩親友</span>
              <h3 class="font-black text-xl text-slate-900">姑媽 & Ryan 表哥 & 表弟</h3>
              <span class="text-xs bg-orange-100 text-orange-800 font-semibold px-2 py-0.5 rounded-full">運動休閒風 ‧ 陽光男孩 ‧ 酷藍色太陽眼鏡</span>
            </div>
            <span class="text-xs text-slate-500 font-medium">於草地活動中一齊玩波、跑跳互動</span>
          </div>

          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <!-- Real Photo -->
            <div class="space-y-2">
              <div class="text-xs font-bold text-slate-600 flex items-center gap-1">
                <span>📸</span> 真人照片參照
              </div>
              <div class="h-72 rounded-xl overflow-hidden bg-slate-200 border border-slate-300 shadow-inner flex items-center justify-center">
                <img src="/assets/raw_photos/aunt_and_cousins/PXL_20260630_180058560.jpg" class="w-full h-full object-cover object-top" alt="Aunt and Cousins Real Photo">
              </div>
              <p class="text-xs text-slate-600 leading-relaxed">姑媽親切溫柔；表哥 Ryan 活潑好動戴運動鏡框；表弟戴著型格藍色遮光太陽眼鏡！</p>
            </div>

            <!-- Rigged Vector Model -->
            <div class="space-y-2">
              <div class="text-xs font-bold text-orange-600 flex items-center gap-1">
                <span>⚡</span> 動畫骨骼矢量模型 (Rigged Vector SVG)
              </div>
              <div class="h-72 rounded-xl overflow-hidden bg-white border-2 border-orange-300 shadow-inner flex items-center justify-center p-3">
                <img src="/assets/characters/auntie_cousins.svg" class="max-h-full object-contain" alt="Auntie and Cousins Vector">
              </div>
              <p class="text-xs text-orange-800 leading-relaxed">三人同框活潑群組模型，Ryan 揮手打招呼，表弟戴著招牌藍色黑超墨鏡！</p>
            </div>
          </div>
        </div>

      </div>
    </div>

    <!-- Section 2: Audio & Voice Narration Review -->
    <div class="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm space-y-4">
      <div class="border-b border-slate-200 pb-3 flex justify-between items-center">
        <div>
          <h2 class="text-xl font-black text-slate-900 flex items-center gap-2">
            <span>🎙️</span> 2. 爸爸真實粵語錄音核對 (Dad's Real Voice Narration)
          </h2>
          <p class="text-sm text-slate-500">已成功降噪並校正電平的 75 秒母語音頻，將作為全劇旁白及口型同步來源。</p>
        </div>
        <span class="text-xs bg-emerald-100 text-emerald-800 font-bold px-3 py-1 rounded-full">
          44.1kHz 錄音質素優良
        </span>
      </div>

      <div class="bg-slate-50 border border-slate-200 rounded-xl p-4 flex flex-col md:flex-row items-center justify-between gap-4">
        <div class="w-full md:w-2/3">
          <audio controls class="w-full">
            <source src="/assets/audio_samples/dad_cantonese_clean.wav" type="audio/wav">
            您的瀏覽器不支持音頻播放。
          </audio>
        </div>
        <div class="text-xs text-slate-600 space-y-1 w-full md:w-1/3">
          <div><strong class="text-slate-800">錄音時長：</strong> 75.54 秒</div>
          <div><strong class="text-slate-800">配音特點：</strong> 親切自然，語調溫暖，咬字清晰標準</div>
          <div><strong class="text-slate-800">聲音處理：</strong> 100% 本地處理，免除第三方收費及私隱外洩</div>
        </div>
      </div>
    </div>

    <!-- Section 3: Next Step Action Bar -->
    <div class="bg-gradient-to-r from-slate-900 to-indigo-950 text-white rounded-2xl p-6 shadow-lg flex flex-col md:flex-row items-center justify-between gap-6">
      <div class="space-y-1">
        <h3 class="text-xl font-bold flex items-center gap-2">
          <span>🚀</span> 造型滿意？我們隨時可以開始 2.5 分鐘動畫生成！
        </h3>
        <p class="text-sm text-slate-300 max-w-2xl">
          一旦您確認角色造型（或提出細節微調），系統將立即自動合成：5 大場景插畫 ➔ 角色骨骼對嘴與運動動畫 ➔ 音效背景音樂混合 ➔ 導出 1080p 本地 MP4 供您試看！
        </p>
      </div>
      <div class="flex flex-col sm:flex-row gap-3 w-full md:w-auto shrink-0">
        <div class="px-6 py-3 bg-emerald-500 text-white font-bold rounded-xl text-center shadow">
          ✨ 請於對話框告訴我反饋或確認！
        </div>
      </div>
    </div>

  </div>
</body>
</html>
"""

def main():
    target_path = "style_showcase.html"
    with open(target_path, "w", encoding="utf-8") as f:
        f.write(HTML_TEMPLATE)
    print(f"Written {target_path} successfully ({os.path.getsize(target_path)} bytes)")

    artifact_dir = r"C:\Users\chish\.gemini\antigravity\brain\706d91eb-30af-4825-a9a0-115b05e85ba1"
    artifact_path = os.path.join(artifact_dir, "style_showcase.html")
    shutil.copy(target_path, artifact_path)
    print(f"Copied to artifact at {artifact_path}")

if __name__ == "__main__":
    main()
