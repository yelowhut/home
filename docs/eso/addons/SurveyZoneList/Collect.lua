SurveyZoneList.Collect = {}

--[[
-- @const string Source name for the character backpack
--]]
SurveyZoneList.Collect.SOURCE_BAG = "bag"

--[[
-- @const string Source name for the account bank (issue #12)
--]]
SurveyZoneList.Collect.SOURCE_BANK = "bank"

-- @var table Keys are the zone key (see SurveyZoneList.Zone), value is a table
-- which contain all info about the zone like number of survey, etc
SurveyZoneList.Collect.zoneList = {}

-- @var table Two levels : [bagId][slotIdx]. Value is a table with info about
-- the survey at the specific slot; it contains the zone key and the itemlink.
SurveyZoneList.Collect.slotList = {}

-- @var table Same as zoneList but with numerical keys (like an array), so we
-- don't care about keys on this table. Values are reference to values in zoneList.
SurveyZoneList.Collect.orderedList = {}

--[[
-- Obtain the list of bags to read.
--
-- The character backpack is always read. The bank is only read when the user
-- asked for it, because it is off by default (issue #12).
--
-- @return table A list of bag ids
--]]
function SurveyZoneList.Collect:bagsToScan()
    local bagList = {BAG_BACKPACK}

    if SurveyZoneList.savedVariables.bank.readBank == true then
        table.insert(bagList, BAG_BANK)
        table.insert(bagList, BAG_SUBSCRIBER_BANK)
    end

    return bagList
end

--[[
-- Obtain the source name a bag belongs to.
--
-- @param integer bagId
--
-- @return string|nil SOURCE_BAG, SOURCE_BANK, or nil for a bag we ignore
--]]
function SurveyZoneList.Collect:sourceForBag(bagId)
    if bagId == BAG_BACKPACK then
        return self.SOURCE_BAG
    end

    if bagId == BAG_BANK or bagId == BAG_SUBSCRIBER_BANK then
        return self.SOURCE_BANK
    end

    return nil
end

--[[
-- Whether a bag is currently watched.
--
-- @param integer bagId
--
-- @return bool
--]]
function SurveyZoneList.Collect:isBagWatched(bagId)
    if bagId == BAG_BACKPACK then
        return true
    end

    if bagId == BAG_BANK or bagId == BAG_SUBSCRIBER_BANK then
        return SurveyZoneList.savedVariables.bank.readBank == true
    end

    return false
end

--[[
-- Read all items in every watched bag to find all surveys and treasure maps.
--]]
function SurveyZoneList.Collect:search()
    self.zoneList    = {}
    self.slotList    = {}
    self.orderedList = {}

    for _, bagId in ipairs(self:bagsToScan()) do
        local bagSize = GetBagSize(bagId)

        for slotIdx = 0, bagSize, 1 do
            local resolved = SurveyZoneList.Zone:resolveSlot(bagId, slotIdx)

            if resolved ~= nil then
                self:addSlot(bagId, slotIdx, resolved)
            end
        end
    end

    self:rebuildOrderedList()
end

--[[
-- Obtain the table skeleton used to save data about a zone.
--
-- @param table resolved The resolution returned by SurveyZoneList.Zone
--
-- @return table
--]]
function SurveyZoneList.Collect:obtainNewZoneInfo(resolved)
    local zoneInfo = {
        key         = resolved.key,
        zoneId      = resolved.zoneId,
        name        = resolved.name,
        nameEscaped = SurveyZoneList.ItemSort:espaceLuaStr(resolved.name:lower()),
        survey      = {
            bag  = {nbUnique = 0, nbTotal = 0},
            bank = {nbUnique = 0, nbTotal = 0},
            all  = {nbUnique = 0, nbTotal = 0},
        },
        treasure    = {
            bag  = {nbUnique = 0, nbTotal = 0},
            bank = {nbUnique = 0, nbTotal = 0},
            all  = {nbUnique = 0, nbTotal = 0},
        },
        craft       = {},
        list        = {},
    }

    for _, craftType in ipairs(SurveyZoneList.Zone.CRAFT_TYPES) do
        zoneInfo.craft[craftType] = {bag = 0, bank = 0, all = 0}
    end

    return zoneInfo
end

--[[
-- Rebuild the array used by the sort and the display.
--]]
function SurveyZoneList.Collect:rebuildOrderedList()
    self.orderedList = {}

    for _, zoneInfo in pairs(self.zoneList) do
        table.insert(self.orderedList, zoneInfo)
    end
end

--[[
-- Record the item held by a bag slot.
--
-- Pure bookkeeping : no alert, no display refresh, no ordered list rebuild.
--
-- @param integer bagId
-- @param integer slotIdx
-- @param table resolved The resolution returned by SurveyZoneList.Zone
--]]
function SurveyZoneList.Collect:addSlot(bagId, slotIdx, resolved)
    local itemLink = GetItemLink(bagId, slotIdx)
    local quantity = GetSlotStackSize(bagId, slotIdx)

    if type(quantity) ~= "number" or quantity <= 0 then
        quantity = 1
    end

    if self.zoneList[resolved.key] == nil then
        self.zoneList[resolved.key] = self:obtainNewZoneInfo(resolved)
    end

    local zoneInfo = self.zoneList[resolved.key]

    if zoneInfo.list[itemLink] == nil then
        zoneInfo.list[itemLink] = {
            isSurvey = resolved.isSurvey,
            craft    = resolved.craft,
            slots    = {},
        }
    end

    local entry = zoneInfo.list[itemLink]

    if entry.slots[bagId] == nil then
        entry.slots[bagId] = {}
    end

    entry.slots[bagId][slotIdx] = quantity

    if self.slotList[bagId] == nil then
        self.slotList[bagId] = {}
    end

    self.slotList[bagId][slotIdx] = {
        zoneKey  = resolved.key,
        itemLink = itemLink,
    }

    self:recomputeZone(zoneInfo)
end

--[[
-- Forget whatever was recorded for a bag slot.
--
-- Pure bookkeeping : no alert, no display refresh, no ordered list rebuild.
-- The zone itself is kept even when it becomes empty, pruneEmptyZones does that.
--
-- @param integer bagId
-- @param integer slotIdx
--]]
function SurveyZoneList.Collect:removeSlot(bagId, slotIdx)
    local slotInfo = self:findForSlot(bagId, slotIdx)

    if slotInfo == nil then
        return
    end

    self.slotList[bagId][slotIdx] = nil

    local zoneInfo = self.zoneList[slotInfo.zoneKey]

    if zoneInfo == nil then
        return
    end

    local entry = zoneInfo.list[slotInfo.itemLink]

    if entry == nil then
        return
    end

    if entry.slots[bagId] ~= nil then
        entry.slots[bagId][slotIdx] = nil
    end

    if self:entryQuantity(entry, self.SOURCE_BAG) <= 0 and self:entryQuantity(entry, self.SOURCE_BANK) <= 0 then
        zoneInfo.list[slotInfo.itemLink] = nil
    end

    self:recomputeZone(zoneInfo)
end

--[[
-- Drop every zone which no longer holds anything.
--]]
function SurveyZoneList.Collect:pruneEmptyZones()
    for zoneKey, zoneInfo in pairs(self.zoneList) do
        if zoneInfo.survey.all.nbTotal <= 0 and zoneInfo.treasure.all.nbTotal <= 0 then
            self.zoneList[zoneKey] = nil
        end
    end
end

--[[
-- Handle a single slot update coming from the game.
--
-- The slot is always cleared then re-read, so a slot whose item changed cannot
-- leave a stale contribution behind. Counter drift used to be the cause of the
-- wrong "last survey here" alerts.
--
-- @param integer bagId
-- @param integer slotIdx
--
-- @return bool true when the display needs a refresh
--]]
function SurveyZoneList.Collect:updateSlot(bagId, slotIdx)
    if self:isBagWatched(bagId) == false then
        return false
    end

    local source = self:sourceForBag(bagId)

    -- Remember what the slot held, to detect a survey the player just used.
    local previousSlotInfo  = self:findForSlot(bagId, slotIdx)
    local previousLink      = nil
    local previousZoneKey   = nil
    local previousIsSurvey  = false
    local previousQuantity  = 0

    if previousSlotInfo ~= nil then
        previousLink    = previousSlotInfo.itemLink
        previousZoneKey = previousSlotInfo.zoneKey

        local previousZone  = self.zoneList[previousZoneKey]
        local previousEntry = nil

        if previousZone ~= nil then
            previousEntry = previousZone.list[previousLink]
        end

        if previousEntry ~= nil then
            previousIsSurvey = previousEntry.isSurvey
            previousQuantity = self:entryQuantity(previousEntry, self.SOURCE_BAG)
        end
    end

    self:removeSlot(bagId, slotIdx)

    local resolved = SurveyZoneList.Zone:resolveSlot(bagId, slotIdx)

    if resolved ~= nil then
        self:addSlot(bagId, slotIdx, resolved)
    end

    if previousSlotInfo == nil and resolved == nil then
        return false
    end

    if source == self.SOURCE_BAG and previousIsSurvey == true then
        self:notifySurveyUsed(previousZoneKey, previousLink, previousQuantity)
    end

    self:pruneEmptyZones()
    self:rebuildOrderedList()

    return true
end

--[[
-- Sum the quantity an item link has in a source.
--
-- @param table entry A value of zoneInfo.list
-- @param string source SOURCE_BAG or SOURCE_BANK
--
-- @return integer
--]]
function SurveyZoneList.Collect:entryQuantity(entry, source)
    local total = 0

    for bagId, slots in pairs(entry.slots) do
        if self:sourceForBag(bagId) == source then
            for _, quantity in pairs(slots) do
                total = total + quantity
            end
        end
    end

    return total
end

--[[
-- Recompute every counter of a zone from its item list.
--
-- Counters are never incremented in place, they are always derived from the
-- item list. A wrong counter therefore cannot survive a single update.
--
-- @param table zoneInfo
--]]
function SurveyZoneList.Collect:recomputeZone(zoneInfo)
    local sourceList = {self.SOURCE_BAG, self.SOURCE_BANK}

    for _, itemType in ipairs({"survey", "treasure"}) do
        for _, source in ipairs(sourceList) do
            zoneInfo[itemType][source].nbUnique = 0
            zoneInfo[itemType][source].nbTotal  = 0
        end

        zoneInfo[itemType].all.nbUnique = 0
        zoneInfo[itemType].all.nbTotal  = 0
    end

    for _, craftType in ipairs(SurveyZoneList.Zone.CRAFT_TYPES) do
        zoneInfo.craft[craftType].bag  = 0
        zoneInfo.craft[craftType].bank = 0
        zoneInfo.craft[craftType].all  = 0
    end

    for itemLink, entry in pairs(zoneInfo.list) do
        local itemType = "treasure"
        if entry.isSurvey == true then
            itemType = "survey"
        end

        local hasAny = false

        for _, source in ipairs(sourceList) do
            local quantity = self:entryQuantity(entry, source)

            if quantity > 0 then
                hasAny = true

                zoneInfo[itemType][source].nbUnique = zoneInfo[itemType][source].nbUnique + 1
                zoneInfo[itemType][source].nbTotal  = zoneInfo[itemType][source].nbTotal + quantity
                zoneInfo[itemType].all.nbTotal      = zoneInfo[itemType].all.nbTotal + quantity

                if entry.isSurvey == true and entry.craft ~= nil and zoneInfo.craft[entry.craft] ~= nil then
                    zoneInfo.craft[entry.craft][source] = zoneInfo.craft[entry.craft][source] + quantity
                    zoneInfo.craft[entry.craft].all     = zoneInfo.craft[entry.craft].all + quantity
                end
            end
        end

        -- "unique" counts distinct survey items, so an item held in both the
        -- backpack and the bank still counts once in the combined total.
        if hasAny == true then
            zoneInfo[itemType].all.nbUnique = zoneInfo[itemType].all.nbUnique + 1
        end
    end
end

--[[
-- Tell the alert system a survey left the backpack.
--
-- Only a real drop matters : it means the player used a survey. Moving a
-- survey to the bank also drops the backpack quantity, which is why the alert
-- system ignores everything while a bank or inventory window is open.
--
-- @param string zoneKey The zone the survey belonged to
-- @param string itemLink The survey item link
-- @param integer previousQuantity Backpack quantity before the update
--]]
function SurveyZoneList.Collect:notifySurveyUsed(zoneKey, itemLink, previousQuantity)
    local zoneInfo = self.zoneList[zoneKey]
    local entry    = nil

    if zoneInfo ~= nil then
        entry = zoneInfo.list[itemLink]
    end

    local currentQuantity = 0
    if entry ~= nil then
        currentQuantity = self:entryQuantity(entry, self.SOURCE_BAG)
    end

    if currentQuantity >= previousQuantity then
        return
    end

    if SurveyZoneList.Alerts:uiOpen() == true then
        return
    end

    local zoneBagTotal = 0
    if zoneInfo ~= nil then
        zoneBagTotal = zoneInfo.survey.bag.nbTotal
    end

    SurveyZoneList.Recolt:reset()
    SurveyZoneList.Alerts:updateQuantity(currentQuantity, zoneBagTotal)
end

--[[
-- Return saved info about the item at a specific slot index in a bag.
--
-- @param integer bagId
-- @param integer slotIdx
--
-- @return table|nil
--]]
function SurveyZoneList.Collect:findForSlot(bagId, slotIdx)
    if self.slotList[bagId] == nil then
        return nil
    end

    return self.slotList[bagId][slotIdx]
end
