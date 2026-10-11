-- Sector stash (satellite view): merges same-class stacks and sorts the items by type, then by name.
--  * The stash (SectorStash, Lua/ItemContainer.lua) is a non-persistent view, rebuilt by SetSectorId from the
--    sector containers and dead units every time it is opened or an inventory tab is pressed (with the tab's
--    filter). Items are laid out in the order they are added, so the sort just re-adds the slot contents in
--    sorted order - only what the selected tab shows is sorted, nothing in the save changes.
--  * Type = inventory tab (Ammo, Weapons, Equipment, Supplies, Other - the tabs' own order), then the item
--    def group (Firearm - Assault, Armor - Kevlar...), caliber for ammo. Then name, condition, amount.
--  * Stacking changes the real sector inventory, so it runs as a NetSyncEvent (co-op safe), then the open
--    stash is rebuilt. Merging works like the vanilla squad bag sort (_SortItemsInBag): fill the biggest
--    stacks, destroy the emptied ones.
--  * SectorStash:ResetBinding (before Take All) rebuilds the stash for a sync op - it keeps vanilla order.

local function Option(name)
	return not CurrentModOptions or CurrentModOptions[name] ~= false
end

-------------------------------------------------- stacking

local function CanStack(item)
	return IsKindOf(item, "InventoryStack") and not item.locked and (item.MaxStacks or 1) > 1
end

-- Not-full stacks of the sector per class, in a deterministic order (same as SectorStash:SetSectorId).
local function CollectStacks(sector_id)
	local sector = gv_Sectors and gv_Sectors[sector_id]
	local by_class, classes = {}, {}
	if not sector then return by_class, classes end
	local function add(item, unit, container)
		if not CanStack(item) or item.Amount >= item.MaxStacks then return end
		local list = by_class[item.class]
		if not list then
			list = {}
			by_class[item.class] = list
			classes[#classes + 1] = item.class
		end
		list[#list + 1] = { item = item, unit = unit, container = container, idx = #list + 1 }
	end
	for _, session_id in ipairs(sector.dead_units or empty_table) do
		local ud = gv_UnitData[session_id]
		if ud and ud:IsDead() then
			ud:ForEachItemInSlot("InventoryDead", function(item) add(item, ud) end)
		end
	end
	for _, container in ipairs(sector.sector_inventory or empty_table) do
		if container[2] then -- opened
			for _, item in sorted_pairs(container[3] or empty_table) do
				add(item, nil, container)
			end
		end
	end
	return by_class, classes
end

local function NeedsMerge(sector_id)
	local by_class = CollectStacks(sector_id)
	for _, list in pairs(by_class) do
		if #list > 1 then return true end
	end
end

-- Same removal as SectorStash:RemoveItem, the container object on the map is synced by the caller.
local function RemoveFromSource(entry)
	if entry.unit then
		entry.unit:RemoveItem("InventoryDead", entry.item)
		return
	end
	local items = entry.container[3]
	local idx = items and table.find(items, entry.item)
	if idx then
		table.remove(items, idx)
	end
end

local function MergeStacks(sector_id)
	local by_class, classes = CollectStacks(sector_id)
	local touched, merged = {}, false
	for _, class in ipairs(classes) do
		local list = by_class[class]
		if #list > 1 then
			table.sort(list, function(a, b)
				if a.item.Amount ~= b.item.Amount then return a.item.Amount > b.item.Amount end
				return a.idx < b.idx
			end)
			local l, r = 1, #list
			while l < r do
				local keeper, donor = list[l].item, list[r]
				if keeper.Amount >= keeper.MaxStacks then
					l = l + 1
				else
					merged = true
					if keeper:MergeStack(donor.item) then
						RemoveFromSource(donor)
						if donor.container then
							table.insert_unique(touched, donor.container)
						end
						DoneObject(donor.item)
						r = r - 1
					end
				end
			end
		end
	end
	for _, container in ipairs(touched) do
		local obj = container[1] ~= "virtual" and HandleToObject[container[1]]
		if IsKindOf(obj, "SectorInventoryObj") then
			obj:SyncWithSectorInventory()
		end
	end
	return merged
end

-- The stash holds the destroyed stacks now; rebuild it with the selected tab's filter, as the tab button does,
-- and clean up the UI as NetSyncEvents.MoveItemsToStash does.
local function RebuildStash(sector_id)
	local stash = gv_SectorInventory
	if not stash or stash.sector_id ~= sector_id then return end
	local dlg = GetMercInventoryDlg()
	local open = dlg and dlg.Mode == "loot" and dlg.context and dlg.context.container == stash
	local tab = open and dlg.selected_tab
	local preset = tab and tab ~= "all" and InventoryTabs[tab]
	stash:Clear()
	stash:SetSectorId(sector_id, preset and function(item) return preset:FilterItem(item) end)
	if open then
		InventoryUIRespawn()
		InventoryDeselectMultiItems(dlg)
	end
end

local stack_pending = {}

function NetSyncEvents.StashSort_Stack(sector_id)
	stack_pending[sector_id] = nil
	if MergeStacks(sector_id) then
		RebuildStash(sector_id)
		Msg("InventoryChange", gv_SectorInventory or false) -- other SectorStash views (map icons) rebuild on it
	end
end

-------------------------------------------------- sorting

local function TabRank(item)
	if not InventoryItemDefs[item.class] then return 99 end -- the Weapons tab filter needs the def
	local tab = InventoryTabs[InventoryFindTab(item)]
	return tab and tab.id ~= "all" and (tab.SortKey or 0) or 99
end

local function SortKey(item)
	local def = InventoryItemDefs[item.class]
	return {
		TabRank(item),
		def and def.group or "",
		IsKindOfClasses(item, "Ammo", "Ordnance") and item.Caliber or "",
		item.DisplayName and _InternalTranslate(item.DisplayName) or item.class,
		-(item.Condition or 0),
		-(item.Amount or 1),
		item.id or 0,
	}
end

local function KeyLess(a, b)
	for i = 1, #a do
		if a[i] ~= b[i] then
			return a[i] < b[i]
		end
	end
	return false
end

-- Row by row, a large item that does not fit the rest of the row goes to the next one. Vanilla first-fit
-- would put later small items into those gaps and break the order.
local function PlaceSorted(stash, items)
	local width = stash:GetSlotData("Inventory").width
	local x, y = 1, 1
	for _, item in ipairs(items) do
		local w = item:GetUIWidth()
		if x + w - 1 > width then
			x, y = 1, y + 1
		end
		if Inventory.AddItem(stash, "Inventory", item, x, y) then
			x = x + w
		else
			Inventory.AddItem(stash, "Inventory", item)
		end
	end
end

local function SortStash(stash)
	local slot = stash.Inventory
	local items = {}
	for i = 2, #slot, 2 do
		items[#items + 1] = slot[i]
	end
	if #items < 2 then return end
	local keys = {}
	for _, item in ipairs(items) do
		keys[item] = SortKey(item)
	end
	table.sort(items, function(a, b) return KeyLess(keys[a], keys[b]) end)
	DoneObject(slot) -- as SectorStash:Clear, the items stay in the sector data
	stash.Inventory = InventorySlot:new()
	PlaceSorted(stash, items)
end

-------------------------------------------------- hooks

local orig_set = rawget(SectorStash, "stashsort_orig_SetSectorId") or SectorStash.SetSectorId
SectorStash.stashsort_orig_SetSectorId = orig_set

function SectorStash:SetSectorId(sector_id, filter)
	local target = sector_id or gv_CurrentSectorId
	local rebuilt = self.sector_id ~= target
	local res = orig_set(self, sector_id, filter)
	if not rebuilt or self ~= gv_SectorInventory or self.sector_id ~= target or rawget(self, "stashsort_vanilla") then
		return res
	end
	-- a tab is auto-pressed when an item is dragged over the stash: do not merge the dragged stack away
	local dragging = rawget(_G, "InventoryDragItem") or rawget(_G, "InventoryDragItems")
	if Option("StackItems") and not dragging and not stack_pending[target] and NeedsMerge(target) then
		stack_pending[target] = true
		NetSyncEvent("StashSort_Stack", target)
	end
	if Option("SortStash") then
		SortStash(self)
	end
	return res
end

local orig_reset = rawget(SectorStash, "stashsort_orig_ResetBinding") or SectorStash.ResetBinding
SectorStash.stashsort_orig_ResetBinding = orig_reset

function SectorStash:ResetBinding(...)
	rawset(self, "stashsort_vanilla", true)
	orig_reset(self, ...)
	rawset(self, "stashsort_vanilla", nil)
end

-- The stash stays bound to the sector between openings (and keeps items dropped in at their spots);
-- unbind it, so opening the inventory rebuilds - and sorts - it. Same condition as vanilla OpenInventory
-- uses to call GetSectorInventory.
local orig_open = rawget(SectorStash, "stashsort_orig_OpenInventory") or OpenInventory
SectorStash.stashsort_orig_OpenInventory = orig_open

function OpenInventory(obj, container, ...)
	local squad = obj and obj.Squad and gv_Squads[obj.Squad]
	if gv_SatelliteView and gv_SectorInventory and not container and squad and not IsSquadTravelling(squad) then
		gv_SectorInventory:Clear()
	end
	return orig_open(obj, container, ...)
end
