"use strict";

void function() {
    /*
    ** Element collections
    */

    function items() {
        return document.querySelectorAll('.selector.item');
    }

    function filters() {
        return document.querySelectorAll('.selector.filter');
    }


    /*
    ** Filter predicates
    */

    var filterPredicates = {
        all: function() {
            return function(e) {
                return true;
            };
        },
        feed: function(options) {
            var feed = options.feed;
            return function(e) {
                return e.dataset.feed == feed;
            };
        },
        unread: function(options) {
            var readInfo = getReadInfo();
            return function(e) {
                return isUnread(readInfo, e.dataset.item);
            };
        }
    };


    /*
    ** UI Update functions
    */

    // Update a "selector collection" to select a new element
    function uiSelect(collection, newSelected) {
        collection().forEach(function(el) {
            el.classList.remove('selector--selected');
        });
        newSelected.classList.add('selector--selected');
    }

    // Update the read/unread status of all `.item` elements for the given item
    // id
    function uiReadStatus(readInfo, id) {
        var unread = isUnread(readInfo, id);
        document.querySelectorAll('.item[data-item="' + id + '"]').forEach(function(el) {
            el.classList.toggle('item--unread', unread);
        });
    }


    /*
    ** Event handlers
    */

    document.addEventListener('DOMContentLoaded', function() {
        // Event handlers for item elements
        items().forEach(function(el) {
            // Clicking on the item element
            el.addEventListener('click', function() {
                // Update UI for newly selected item
                uiSelect(items, el);

                // Navigate item viewer to item page
                document.querySelector('#item-view').src = 'items/' + el.dataset.item + '.html';

                // Mark the item as read
                var readInfo = getReadInfo();
                markAsRead(readInfo, el.dataset.item);
                uiReadStatus(readInfo, el.dataset.item);
                storeReadInfo(readInfo);
            });

            // Click on the read/unread status element
            el.querySelector('button[value="status"]').addEventListener('click', function(e) {
                // Prevent click from actually navigating to the item
                e.stopPropagation();

                // Mark the item as the inverted status
                var readInfo = getReadInfo();
                if(isRead(readInfo, el.dataset.item)) {
                    markAsUnread(readInfo, el.dataset.item);
                } else {
                    markAsRead(readInfo, el.dataset.item);
                }
                uiReadStatus(readInfo, el.dataset.item);
                storeReadInfo(readInfo);
            });
        });

        // Filters event handlers
        filters().forEach(function(el) {
            // CLick on a filter
            el.addEventListener('click', function() {
                // Update UI for newly selected filter
                uiSelect(filters, el);

                // Filter item list with the filter type predicate
                var pred = filterPredicates[el.dataset.filterType](el.dataset);
                items().forEach(function(e) {
                    e.classList.toggle('hidden', !pred(e));
                });
            });
        });

        // Global "Mark all read" button events
        document.querySelectorAll('button[value="mark-all"]').forEach(function(el) {
            // Click on the mark all read button
            el.addEventListener('click', function() {
                var highest = 1;
                // Determine highest item id (and update the UI in passing)
                items().forEach(function(el) {
                    highest = Math.max(highest, parseInt(el.dataset.item));
                    el.classList.remove('item--unread');
                });
                // Update the read info data
                var readInfo = getReadInfo();
                markAllAsRead(readInfo, highest);
                storeReadInfo(readInfo);
            });
        });

        // Filtered item list "Mark all read" button events
        document.querySelectorAll('button[value="mark-filtered"]').forEach(function(el) {
            // Click on the button
            el.addEventListener('click', function() {
                var readInfo = getReadInfo();
                items().forEach(function(el) {
                    // Item is filtered, so we ignore it
                    if(el.classList.contains('hidden')) {
                        return;
                    }
                    // Mark the current item as read, and update the UI
                    markAsRead(readInfo, el.dataset.item);
                    el.classList.remove('item--unread');
                });
                storeReadInfo(readInfo);
            });
        });
    });


    /*
    ** Unread Handling
    */

    /*
    Unread handling is used to keep track of what news item have already been
    read by the user. Conceptually, any news item has a read/unread state, and
    these can be arbitrarily set.

    Additionally, when new items appear, they should automatically take the
    unread state. The sequence of item numbers is guaranteed to increase
    monotonically, but not necessarily sequential.

    Because most read-unread churn occurs at the most-recent side of the items,
    the read info uses a compact representation. Unread handling is based on a
    data structure called read info. Read info consists of three fields:

        { readThreshold: 0, readSet: [], unreadSet: [] }

    The `readThreshold` is used to indicate the default state of a news item.
    All items for which `id < readThreshold` holds are considered read, and all
    items for which `id >= readThreshold` holds are considered unread.

    To allow arbitrary assignment of read/unread status, the two arrays of items
    called `readSet` and `unreadSet` are used to override the item state derived
    from the `readThreshold`. Any items listed in `readSet` are considered read,
    and any items listed in `unreadSet` are considered unread.
    */

    /*
    Note: the read info structure is not turned into a "proper" class because
    this adds very little value in this case, while it does create a situation
    where both methods and global functions are needed to interact with the
    concept.
    */

    // Initializes local storage with a "nothing is read" state
    function initLocalStorage() {
        storeReadInfo({
            readThreshold: 1,
            readSet: new Set(),
            unreadSet: new Set()
        });
    }

    // Retrieves the current read info from local storage
    function getReadInfo() {
        return {
            readThreshold: parseInt(window.localStorage.getItem('readThreshold')),
            readSet: new Set(JSON.parse(window.localStorage.getItem('readSet'))),
            unreadSet: new Set(JSON.parse(window.localStorage.getItem('unreadSet')))
        };
    }

    // Store a read info to local storage
    function storeReadInfo(readInfo) {
        compactReadInfo(readInfo);
        window.localStorage.setItem('readThreshold', readInfo.readThreshold);
        window.localStorage.setItem('readSet', JSON.stringify(Array.from(readInfo.readSet)));
        window.localStorage.setItem('unreadSet', JSON.stringify(Array.from(readInfo.unreadSet)));
    }

    // Compacts a read info in place
    function compactReadInfo(readInfo) {
        // Clean up read/unread sets by dropping duplicate items, filtering out
        // anything already indicated by the readThreshold, and sorting them
        function filterSet(set, pred) {
            return new Set(Array.from(set).filter(pred));
        }
        readInfo.readSet = filterSet(readInfo.readSet, function(a){ return a >= readInfo.readThreshold });
        readInfo.unreadSet = filterSet(readInfo.unreadSet, function(a){ return a < readInfo.readThreshold });

        // If both sets are empty, we are done, since we cannot make the
        // representation any more compact
        if(readInfo.readSet.size + readInfo.unreadSet.size == 0) {
            return;
        }

        // Determine highest and lowest thresholds we are interested in
        var combined = Array.from(readInfo.readSet).concat(Array.from(readInfo.unreadSet), [readInfo.readThreshold]);
        var low = Math.min.apply(null, combined) - 1;
        var high = Math.max.apply(null, combined) + 1;
        // Make sure that low does not go below 0
        low = Math.max(low, 1);

        // Create a working copy of the read info
        var working = {
            readThreshold: readInfo.readThreshold,
            readSet: new Set(readInfo.readSet),
            unreadSet: new Set(readInfo.unreadSet)
        };

        // Stores the working copy to the actual read info
        function storeWorking() {
            readInfo.readThreshold = working.readThreshold;
            readInfo.readSet = new Set(working.readSet);
            readInfo.unreadSet = new Set(working.unreadSet);
        }

        // Moves the read threshold down one place in the working copy
        function down(info) {
            var newT = Math.max(info.readThreshold - 1, 1);
            if(info.readThreshold == newT) return;
            if(info.unreadSet.has(newT)) {
                info.unreadSet.delete(newT);
            } else {
                info.readSet.add(newT);
            }
            info.readThreshold = newT;
        }

        // Moves the read threshold up one place in the working copy
        function up(info) {
            var newT = info.readThreshold + 1;
            if(info.readSet.has(info.readThreshold)) {
                info.readSet.delete(info.readThreshold);
            } else {
                info.unreadSet.add(info.readThreshold);
            }
            info.readThreshold = newT;
        }

        // Move down to the lowest threshold of interest
        while(working.readThreshold != low) {
            down(working);
        }

        // Determine current score and store working state to actual
        var best = working.readSet.size + working.unreadSet.size;
        storeWorking();

        // Move up to the highest threshold of interest, and store the most
        // compact variant so far in the actual read info
        while(working.readThreshold != high) {
            up(working);
            if(working.readSet.size + working.unreadSet.size <= best) {
                best = working.readSet.size + working.unreadSet.size;
                storeWorking();
            }
        }
    }

    // Mutates the read info by marking the id as read
    function markAsRead(readInfo, id) {
        var id = parseInt(id);
        readInfo.readSet.add(id);
        readInfo.unreadSet.delete(id);
    }

    // Mutates the read info by marking the id as unread
    function markAsUnread(readInfo, id) {
        var id = parseInt(id);
        readInfo.readSet.delete(id);
        readInfo.unreadSet.add(id);
    }

    // Mutates the read info by marking everything up to the given id as read
    function markAllAsRead(readInfo, upto) {
        readInfo.readSet.clear();
        readInfo.unreadSet.clear();
        readInfo.readThreshold = upto + 1;
    }

    // Checks if an item is read
    function isRead(readInfo, id) {
        var id = parseInt(id);
        // Check threshold state...
        if(id < readInfo.readThreshold) {
            // ...if the item is below the threshold and not in the unread set,
            // it is read
            return !readInfo.unreadSet.has(id)
        } else {
            // ...if the item is above the threshold, it is unread unless it is
            // in the read set
            return readInfo.readSet.has(id);
        }
    }

    // Checks if an item is unread
    function isUnread(readInfo, id) {
        return !isRead(readInfo, id);
    }

    // When the document is ready, initialize the storage and update the UI
    document.addEventListener('DOMContentLoaded', function() {
        // Check for database id, and initialize storage if it's missing or
        // different from the expected id
        var currentId = window.localStorage.getItem('databaseId');
        if(!currentId || currentId != databaseId) {
            window.localStorage.setItem('databaseId', databaseId);
            initLocalStorage();
        }

        var readInfo = getReadInfo();
        items().forEach(function(el) {
            el.classList.toggle('item--unread', isUnread(readInfo, el.dataset.item));
        });
    });

}();
