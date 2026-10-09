-- Double click on an item in a loot container (sector stash, dropped container, dead enemy) scraps it,
-- together with all items of the same kind in that container with the same or worse condition.
-- Items with 0 scrap parts (grenades, pipe bombs...) are simply destroyed, as in Interface tweaks
-- (steam 3274998887), where the idea comes from.
--  * Alt + double click keeps the vanilla action (equip / move to the squad bag).
--  * Squad bag, living units and mercs' bodies are never scrapped from; neither are valuables, quest
--    items, locked items and squad bag items (ammo, parts, explosive substances...) - for those the
--    vanilla double click moves them to the squad bag.
-- The scrap itself goes through the vanilla "scrap" squad bag action (NetSquadBagAction -> ScrapItem),
-- the same path as the SCRAP / SCRAP ALL context menu entries.

local function CanScrapFrom(container)
	if not container or IsKindOf(container, "SquadBag") then
		return false
	end
	if IsKindOfClasses(container, "Unit", "UnitData") and (not container:IsDead() or container:IsMerc()) then
		return false
	end
	return true
end

local function CanScrapItem(item)
	return IsKindOf(item, "InventoryItem") and not item.locked
		and not IsKindOfClasses(item, "SquadBagItem", "Valuables", "QuestItem")
end

local function CollectSame(container, slot_name, item)
	if not CurrentModOptions.ScrapInBulk then
		return { item }
	end
	local items = {}
	local condition = item.Condition
	container:ForEachItemInSlot(slot_name, function(other)
		if other.class == item.class and not other.locked
			and (not condition or (other.Condition or 0) <= condition) then
			items[#items + 1] = other
		end
	end)
	if not table.find(items, item) then
		items[#items + 1] = item
	end
	return items
end

local function ScrapItems(container, slot_name, items)
	local unit = GetInventoryUnit()
	local bag = unit and unit.Squad and GetSquadBagInventory(unit.Squad)
	if not bag then return false end

	local ids, count, parts = {}, 0, 0
	for _, it in ipairs(items) do
		local amount = IsKindOf(it, "InventoryStack") and it.Amount or 1
		ids[#ids + 1] = it.id
		count = count + amount
		parts = parts + it:AmountOfScrapPartsFromItem() * amount
	end
	local name = _InternalTranslate(items[1].DisplayName)
	NetSquadBagAction(unit, container, slot_name, ids, bag, "scrap", 0)
	PlayFX("Scrap", "start", items[1])
	CombatLog("short", Untranslated(string.format("Разобрано: %d x %s, получено частей: %d", count, name, parts)))
	return true
end

local orig_dbl = rawget(BrowseInventorySlot, "invqol_orig_OnMouseButtonDoubleClick") or BrowseInventorySlot.OnMouseButtonDoubleClick
BrowseInventorySlot.invqol_orig_OnMouseButtonDoubleClick = orig_dbl

function BrowseInventorySlot:OnMouseButtonDoubleClick(pt, button, source)
	if button ~= "L" or not CurrentModOptions.DoubleClickScrap or terminal.IsKeyPressed(const.vkAlt)
		or IsMouseViaGamepadActive() or rawget(_G, "WasDraggingLastLMBClick") then
		return orig_dbl(self, pt, button, source)
	end
	local dlgContext = GetDialogContext(self)
	if dlgContext and InventoryDisabled(dlgContext) or not InventoryIsContainerOnSameSector({ context = self.context }) then
		return orig_dbl(self, pt, button, source)
	end

	local container = self.context
	local dragged = rawget(_G, "InventoryDragItem")
	local item = dragged
	if not item then
		local _
		_, item = self:FindItemWnd(pt)
	end
	if not item or not CanScrapFrom(container) or not CanScrapItem(item)
		or not container:GetItemPos(item) then
		return orig_dbl(self, pt, button, source)
	end

	if dragged then
		self:CancelDragging()
	end
	ScrapItems(container, self.slot_name, CollectSame(container, self.slot_name, item))
	return "break"
end
