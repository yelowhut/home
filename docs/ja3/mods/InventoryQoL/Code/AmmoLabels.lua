-- Caliber / type labels on top of ammo, ordnance and grenade tiles - in the inventory and in the craft
-- operation lists. Idea taken from "Show ammo calibers" of Interface tweaks (steam 3274998887), which is
-- disabled because it hangs the sector stash. English item names only (the game runs in English).
--
-- XInventoryItem:OnContextUpdate is wrapped, not replaced: vanilla runs first, then the label goes to
-- idTopRightText, which vanilla uses only for weapon/armor condition. XActivityItem (craft/repair lists)
-- calls XInventoryItem.OnContextUpdate explicitly, so it gets the label too; CraftQueue.lua re-applies it
-- after shrinking the craft tiles.

local TypeAbbr = {
	{ "armor piercing", "AP" }, { "hollow point", "HP" }, { "subsonic", "SS" }, { "tracer", "TR" },
	{ "match", "M" }, { "shock", "SH" }, { "explosive", "EXP" }, { "frag", "FRAG" }, { "slap", "SLAP" },
	{ "incendiary", "INC" }, { "breacher", "BR" }, { "sabot", "SAB" }, { "saltshot", "SALT" },
	{ "buckshot", "" }, { "standard", "" }, { "basic", "" }, { "point", "HP" },
}

local CaliberRules = {
	{ "×", "x" },
	{ "(%d)%s*x%s*(%d)", "%1x%2" },
	{ "%s*mm", "" },
	{ "(%d+)%-gauge", "%1g" },
	{ " Lapua Magnum", "LM" },
	{ " HR Magnum", "HR" },
	{ " Magnum", "Mag" },
	{ " Special", "Spl" },
	{ " Blackout", "BLK" },
	{ " WinMag", "WM" },
	{ "Win$", "" },
	{ " British", "Brit" },
	{ " Creedmoor", "CM" },
	{ " Grendel", "Gr" },
	{ " ChayTac", "CT" },
	{ " Mauser", "" },
	{ "%s*ACP", "" },
	{ "S&W", "" },
	{ " AE", "AE" },
	{ " AMP", "AMP" },
	{ " NATO", "N" },
	{ " WP", "WP" },
}

local NameMap = {
	["grenade"] = "Frag", ["stick grenade"] = "Stick", ["smoke grenade"] = "Smoke",
	["tear gas grenade"] = "Tear", ["mustard gas grenade"] = "Mustard", ["flashbang"] = "Flash",
	["molotov cocktail"] = "Molotov", ["pipe bomb"] = "Pipe", ["shaped charge"] = "Shaped",
	["demo charge"] = "Demo", ["mortar cartridge"] = "HE", ["mortar gas cartridge"] = "Gas",
	["mortar smoke cartridge"] = "Smoke", ["flare cartridge"] = "Flare", ["he rocket"] = "HE",
	["40 mm he"] = "40 HE", ["40 mm flashbang"] = "40 Flash",
}

local TriggerAbbr = {
	Proximity = "Prox", Timed = "Time", Remote = "Rem", ["Proximity-Timed"] = "P-T",
}

local function Trim(s)
	return (s:gsub("^%s+", ""):gsub("%s+$", ""):gsub("%s%s+", " "))
end

local function ShortCaliber(s)
	for _, rule in ipairs(CaliberRules) do
		s = s:gsub(rule[1], rule[2])
	end
	return Trim(s)
end

local function Join(a, b)
	return (b and b ~= "") and (a .. " " .. b) or a
end

-- Returns the full label and a shorter fallback (case length dropped), or nil.
local function MakeLabels(name, is_ammo, trigger)
	name = Trim(name)
	local lname = name:lower()
	if NameMap[lname] then
		return NameMap[lname]
	end
	local cal, rest = name:match("^(%d+mm %u+) (%a+) rifle grenade$")
	if cal then
		return Join(ShortCaliber(cal), rest)
	end
	if is_ammo then
		for _, t in ipairs(TypeAbbr) do
			local key = t[1]
			if lname:sub(-#key - 1) == " " .. key then
				local caliber = ShortCaliber(name:sub(1, #name - #key - 1))
				local short = caliber:gsub("^([%.%d]+)x%d+", "%1")
				return Join(caliber, t[2]), Join(short, t[2])
			end
		end
		return ShortCaliber(name)
	end
	-- traps (C4/TNT/PETN): explosive + current trigger, which can be changed in game
	if trigger then
		local base = name:gsub("^Proximity ", ""):gsub("^Remote ", ""):gsub("^Timed ", "")
		return Join(base, TriggerAbbr[trigger])
	end
	local generic = Trim(name:gsub("%s*[Gg]renade", ""):gsub("%s*[Cc]artridge", ""):gsub("%s*[Cc]ocktail", ""))
	if #generic > 10 then
		generic = generic:match("^(%S+)") or generic
	end
	return generic ~= "" and generic or nil
end

local LabelStyles = { "InventoryItemsCount", "InventoryItemsCountMax", "InventoryRolloverPropSmall" }
local DefaultColor = 4291018156 -- InventoryItemsCount text color
local font_ids = {}

local function FontId(style)
	local id = font_ids[style]
	if not id then
		id = UIL.GetFontID(_InternalTranslate(TextStyles[style].TextFont))
		font_ids[style] = id
	end
	return id
end

local function EnglishName(item)
	local name = item.DisplayName
	if not name or name == "" then return end
	local get = rawget(_G, "TDevModeGetEnglishText")
	local ok, text = pcall(get or _InternalTranslate, name)
	if ok and type(text) == "string" and text ~= "Missing text" then
		return text
	end
	return _InternalTranslate(name)
end

local function LabelColor(item)
	local style = item.colorStyle and TextStyles[item.colorStyle]
	local r, g, b = GetRGB(style and style.TextColor or DefaultColor)
	return string.format("<color %d %d %d>", r, g, b)
end

local function ResetLabel(self, item)
	if not rawget(self, "invqol_labeled") then return end
	rawset(self, "invqol_labeled", false)
	local text = self.idTopRightText
	text:SetTextStyle("InventoryItemsCount")
	text:SetPadding(box(2, 6, 10, 2))
	text:SetTextHAlign("right")
	if not IsKindOfClasses(item, "Armor", "Firearm", "HeavyWeapon", "MeleeWeapon", "ToolItem", "Medicine") then
		text:SetText("")
	end
	local icon = rawget(self.idItemImg, "idItemAmmoTypeImg")
	if icon then icon:SetVisible(true) end
end

function InvQoL_ApplyLabel(self, item)
	if not item or not rawget(self, "idTopRightText") then return end
	if not CurrentModOptions.CaliberLabels or not IsKindOfClasses(item, "Ammo", "Ordnance", "Grenade") then
		return ResetLabel(self, item)
	end
	local name = EnglishName(item)
	local full, short = MakeLabels(name or "", IsKindOf(item, "Ammo"),
		IsKindOf(item, "ThrowableTrapItem") and item.TriggerType or nil)
	if not full then
		return ResetLabel(self, item)
	end
	-- the full label in a smaller font beats the short one, but the smallest font is the last resort
	local budget = Max(20, self:GetMaxWidth() - 8)
	short = short ~= full and short or nil
	local candidates = {
		{ full, LabelStyles[1] }, { full, LabelStyles[2] }, short and { short, LabelStyles[2] },
		{ full, LabelStyles[3] }, short and { short, LabelStyles[3] },
	}
	local label, style
	for i = 1, 5 do
		local c = candidates[i]
		if c and UIL.MeasureText(c[1], FontId(c[2])) <= budget then
			label, style = c[1], c[2]
			break
		end
	end
	label = label or short or full
	style = style or LabelStyles[3]

	rawset(self, "invqol_labeled", true)
	local text = self.idTopRightText
	text:SetTextStyle(style)
	text:SetPadding(box(4, 4, 4, 0))
	text:SetTextHAlign("left")
	text:SetText(Untranslated(LabelColor(item) .. label .. "</color>"))
	local icon = rawget(self.idItemImg, "idItemAmmoTypeImg")
	if icon then
		icon:SetVisible(not CurrentModOptions.HideAmmoTypeIcon)
	end
end

local orig_update = rawget(XInventoryItem, "invqol_orig_OnContextUpdate") or XInventoryItem.OnContextUpdate
XInventoryItem.invqol_orig_OnContextUpdate = orig_update

function XInventoryItem:OnContextUpdate(item, ...)
	orig_update(self, item, ...)
	InvQoL_ApplyLabel(self, item)
end

InvQoL_MakeLabels = MakeLabels
