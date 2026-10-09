-- Craft operations (Craft Ammo / Craft Explosives, incl. recipes added by mods):
--  * smaller recipe tiles in the "all recipes" list, so more of them fit on screen (size is a mod option);
--  * right click on a recipe adds it to the craft queue, right click on a queued recipe removes it.
-- Vanilla already greys out recipes without resources and sorts them to the end
-- (SectorOperationValidateItemsToCraft), so that part is left as is.

local VanillaTile = 72

local function CraftOperationOf(list)
	local ctx = list and list.context and list.context[1]
	local operation_id = ctx and ctx.operation
	return operation_id and IsCraftOperationId(operation_id) and operation_id or nil
end

local function CraftTileSize()
	return tonumber(CurrentModOptions.CraftTileSize) or VanillaTile
end

local orig_activity_update = rawget(XActivityItem, "invqol_orig_OnContextUpdate") or XActivityItem.OnContextUpdate
XActivityItem.invqol_orig_OnContextUpdate = orig_activity_update

function XActivityItem:OnContextUpdate(item, ...)
	orig_activity_update(self, item, ...)
	local size = CraftTileSize()
	local list = GetParentOfKind(self, "XDragContextWindow")
	if size ~= VanillaTile and list and list.slot_name == "AllItems" and CraftOperationOf(list) then
		local w, h = item:GetUIWidth(), item:GetUIHeight()
		local width = size * w + (w > 1 and 7 or 0)
		self:SetMinWidth(width)
		self:SetMaxWidth(width)
		self:SetMinHeight(size * h)
		self:SetMaxHeight(size * h)
		self.idItemPad:SetMinWidth(width)
		self.idItemPad:SetMaxWidth(width)
		local pad = Max(6, MulDivRound(15, size, VanillaTile))
		self.idItemImg:SetPadding(box(pad, pad, pad, pad))
	end
	InvQoL_ApplyLabel(self, item)
end

local function FindEntryWnd(list, pt)
	for _, wnd in ipairs(list) do
		if wnd:MouseInWindow(pt) and rawget(wnd, "idItem") then
			return wnd
		end
	end
end

-- Same bookkeeping as the vanilla double click (XDragContextWindow:OnMouseButtonDoubleClick).
local function ToggleQueued(list, pt)
	local operation_id = CraftOperationOf(list)
	if not operation_id or not CurrentModOptions.RightClickQueue then return end
	local wnd = FindEntryWnd(list, pt)
	local data = wnd and rawget(wnd.idItem, "item")
	if not data then return "break" end
	local dlg = GetDialog(list)
	local sector_id = dlg and dlg.context and dlg.context.Id
	if not sector_id then return "break" end

	local queue, all = SectorOperationItems_GetTables(sector_id, operation_id)
	if list.slot_name == "AllItems" then
		if not data.enabled or not wnd.idItem:GetEnabled() then return "break" end
		local def = SectorOperation_FindItemDef(data)
		local width = def and def:IsLargeItem() and 2 or 1
		if SectorOperationItems_ItemsCount(queue) + width > 9 then return "break" end
		table.insert(queue, table.copy(data))
	elseif list.slot_name == "ItemsQueue" then
		local idx = table.find(queue, data) or table.find(queue, "recipe", data.recipe)
		if not idx then return "break" end
		table.remove(queue, idx)
	else
		return
	end
	SectorOperationValidateItemsToCraft(sector_id, operation_id)
	NetSyncEvent("SectorOperationItemsUpdateLists", sector_id, operation_id, TableWithItemsToNet(all), TableWithItemsToNet(queue))
	SectorOperation_ItemsUpdateItemLists(dlg:ResolveId("node"))
	return "break"
end

-- The recipe tile gets the click first; a disabled tile does not, then the list itself does.
local orig_item_down = rawget(XActivityItem, "invqol_orig_OnMouseButtonDown") or XActivityItem.OnMouseButtonDown
XActivityItem.invqol_orig_OnMouseButtonDown = orig_item_down

function XActivityItem:OnMouseButtonDown(pt, button)
	if button == "R" then
		local list = GetParentOfKind(self, "XDragContextWindow")
		if list and not list.drag_win and CraftOperationOf(list) then
			local res = ToggleQueued(list, pt)
			if res then return res end
		end
	end
	return orig_item_down and orig_item_down(self, pt, button)
end

local orig_list_down = rawget(XDragContextWindow, "invqol_orig_OnMouseButtonDown") or XDragContextWindow.OnMouseButtonDown
XDragContextWindow.invqol_orig_OnMouseButtonDown = orig_list_down

function XDragContextWindow:OnMouseButtonDown(pt, button)
	if button == "R" and not self.drag_win and CraftOperationOf(self) then
		local res = ToggleQueued(self, pt)
		if res then return res end
	end
	return orig_list_down and orig_list_down(self, pt, button)
end
