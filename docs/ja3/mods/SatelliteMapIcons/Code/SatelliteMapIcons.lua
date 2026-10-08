-- Makes the default satellite map filter show everything at once. Wraps XSatelliteViewMap:UpdateSectorVisuals
-- (Lua/UI/XSatelliteMap.lua) and rearranges the sector icons, all built from vanilla templates/images:
--   top-left: sector id (vanilla), top-right: POI side icon (vanilla), center: squads / main POI (vanilla),
--   bottom-left: Intel, bottom-center: quest (Notes) badge, bottom-right: stash item count.
-- Only the default filter (filter_info_mode == false) is changed; the other filters stay vanilla.

local function Option(name)
	return not CurrentModOptions or CurrentModOptions[name] ~= false
end

-- Same lookup as the vanilla Notes filter: quests of the sector, or of its under/overground pair.
local function GetAllSectorQuests(sector_id)
	local quests = GetQuestsAssociatedWithSector(sector_id)
	if #quests == 0 then
		local otherSectorId = GetUnderOrOvergroundId(sector_id)
		if otherSectorId then
			quests = GetQuestsAssociatedWithSector(otherSectorId)
		end
	end
	return quests
end

local function UpdateQuestMarker(window, sector_id)
	local marker = window.idQuestMarker
	if Option("ShowAllQuests") then
		-- vanilla spawned a marker for the tracked quest only; replace it with all quests (vanilla respawns every update too)
		if marker then
			marker:Close()
			marker = false
		end
		local quests = GetAllSectorQuests(sector_id)
		if #quests > 0 then
			marker = XTemplateSpawn("SatelliteQuestIcon", window, { sector = gv_Sectors[sector_id], quest = quests })
			marker:SetId("idQuestMarker")
			marker:SetImage("UI/Icons/SateliteView/main_quest")
			rawset(marker, "questMode", false)
			if window.window_state == "open" then marker:Open() end
		end
	end
	if marker then
		marker:SetHAlign("center")
		marker:SetVAlign("bottom")
		marker:SetScaleModifier(point(1000, 1000))
	end
end

-- The underground switch button lives in the bottom-right corner too; the stash icon goes above it then.
local function SetStashIconLayout(icon, corner, raised)
	local layout = corner and (raised and "raised" or "corner") or "center"
	if rawget(icon, "SatMapIconsLayout") == layout then return end
	rawset(icon, "SatMapIconsLayout", layout)
	if corner then
		icon:SetHAlign("right")
		icon:SetVAlign("bottom")
		icon:SetScaleModifier(point(1000, 1000))
		icon:SetMargins(box(0, 0, 10, raised and 84 or 10))
	else -- SatelliteStashIcon template defaults, used by the vanilla stash filter
		icon:SetHAlign("center")
		icon:SetVAlign("center")
		icon:SetScaleModifier(point(2000, 2000))
		icon:SetMargins(empty_box)
	end
end

local function UpdateStashIcon(window, sector_id, icon)
	local show = Option("ShowStash")
	local stash = icon and icon.context
	if not stash and show then
		local sector = gv_Sectors[sector_id]
		if next(sector.sector_inventory or empty_table) or next(sector.dead_units or empty_table) then
			stash = PlaceObject("SectorStash")
			stash:SetSectorId(sector_id)
		end
	end
	show = show and stash and stash:CountItemsInSlot("Inventory") >= 1

	if icon then
		rawset(window, "idStashIcon", icon)
		if not show then
			icon:Close() -- also destroys the stash object
			return
		end
	elseif show then
		icon = XTemplateSpawn("SatelliteStashIcon", window, stash)
		icon:SetId("idStashIcon")
		if window.window_state == "open" then icon:Open() end
	else
		if stash then DoneObject(stash) end
		return
	end
	SetStashIconLayout(icon, true, not not window.idUndergroundIconsList)
end

local UpdateSectorVisuals = XSatelliteViewMap.UpdateSectorVisuals

function XSatelliteViewMap:UpdateSectorVisuals(sector_id)
	local window = self.sector_to_wnd[sector_id]
	if self.suppress_visual_updates or self.filter_info_mode or not window then
		UpdateSectorVisuals(self, sector_id)
		-- an icon made in the default filter is reused by the vanilla stash filter
		local stashIcon = window and window.idStashIcon
		if stashIcon then SetStashIconLayout(stashIcon, false) end
		return
	end

	-- vanilla closes the stash icon outside the stash filter, so hide it for the call
	local stashIcon = rawget(window, "idStashIcon")
	if stashIcon then rawset(window, "idStashIcon", nil) end
	UpdateSectorVisuals(self, sector_id)

	local sector = gv_Sectors[sector_id]
	if window.idIntelMarker then
		window.idIntelMarker:SetVisible(Option("ShowIntel") and sector.Intel and sector.intel_discovered)
	end
	UpdateQuestMarker(window, sector_id)
	UpdateStashIcon(window, sector_id, stashIcon)
end

-- Stash icons cache their items; rebuild them and add/remove icons when an inventory changes.
function OnMsg.InventoryChange()
	local ui = g_SatelliteUI
	if not ui or ui.filter_info_mode or ui.window_state == "destroying" then return end
	if ui:GetThread("SatMapIcons-stash-refresh") then return end
	ui:CreateThread("SatMapIcons-stash-refresh", function()
		for sector_id, window in pairs(ui.sector_to_wnd) do
			local icon = window.idStashIcon
			local stash = icon and icon.context
			if stash then
				stash:Clear()
				stash:SetSectorId(sector_id)
				ObjModified(stash)
			end
		end
		ui:UpdateAllSectorVisuals()
	end)
end

function OnMsg.ApplyModOptions(id)
	if id ~= CurrentModId then return end
	if g_SatelliteUI and g_SatelliteUI.window_state ~= "destroying" then
		g_SatelliteUI:DelayedUpdateAllSectorVisuals()
	end
end
