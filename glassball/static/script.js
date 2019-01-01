"use strict";

void function() {
    function items() {
        return document.querySelectorAll('.selector.item');
    }

    function filters() {
        return document.querySelectorAll('.selector.filter');
    }

    var filterTypes = {
        all: function() {
            items().forEach(function(e) {
                e.classList.remove('hidden');
            });
        },
        feed: function(options) {
            var feed = options.feed;
            items().forEach(function(e) {
                if(e.dataset.feed == feed) {
                    e.classList.remove('hidden');
                } else {
                    e.classList.add('hidden');
                }
            });
        },
        unread: function(options) {
            var readInfo = getReadInfo();
            items().forEach(function(e) {
                if(isRead(readInfo, e.dataset.item)) {
                    e.classList.add('hidden');
                } else {
                    e.classList.remove('hidden');
                }
            });
        }
    };

    function uiSelect(collection, entry) {
        collection().forEach(function(el) {
            el.classList.remove('selector--selected');
        })
        entry.classList.add('selector--selected');
    }

    function uiReadStatus(readInfo, id) {
        document.querySelectorAll('.selector[data-item="' + id + '"]').forEach(function(el) {
            if(isRead(readInfo, id)) {
                el.classList.remove('item--unread');
            } else {
                el.classList.add('item--unread');
            }
        })
    }

    document.addEventListener('DOMContentLoaded', function() {
        items().forEach(function(el) {
            el.addEventListener('click', function() {
                // Update UI for newly selected item
                uiSelect(items, el);

                // Navigate item viewer to item page
                document.querySelector('#item-view').src = el.dataset.item + '.html';

                var readInfo = getReadInfo();
                markAsRead(readInfo, el.dataset.item);
                uiReadStatus(readInfo, el.dataset.item);
                storeReadInfo(readInfo);
            });
            el.querySelector('button[value="status"]').addEventListener('click', function(e) {
                e.stopPropagation();
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

        filters().forEach(function(el) {
            el.addEventListener('click', function() {
                // Update UI for newly selected filter
                uiSelect(filters, el);

                // Filter item list
                filterTypes[el.dataset.filterType](el.dataset);
            });
        });

        document.querySelectorAll('button[value="mark-all"]').forEach(function(el) {
            el.addEventListener('click', function() {
                // Determine highest item id
                var highest = 1;
                items().forEach(function(el) {
                    var id = parseInt(el.dataset.item);
                    if(id > highest) {
                        highest = id;
                    }
                    el.classList.remove('item--unread');
                });
                var readInfo = getReadInfo();
                markAllAsRead(readInfo, highest);
                storeReadInfo(readInfo);
            });
        });

        document.querySelectorAll('button[value="mark-filtered"]').forEach(function(el) {
            el.addEventListener('click', function() {
                // Determine highest item id
                var readInfo = getReadInfo();
                items().forEach(function(el) {
                    if(!el.classList.contains('hidden')) {
                        markAsRead(readInfo, el.dataset.item);
                        el.classList.remove('item--unread');
                    }
                });
                storeReadInfo(readInfo);
            });
        });
    });


    //
    // Unread Handling
    //

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

    function initLocalStorage() {
        storeReadInfo({
            readThreshold: 1,
            readSet: new Set(),
            unreadSet: new Set()
        });
    }

    function getReadInfo() {
        return {
            readThreshold: parseInt(window.localStorage.getItem('readThreshold')),
            readSet: new Set(JSON.parse(window.localStorage.getItem('readSet'))),
            unreadSet: new Set(JSON.parse(window.localStorage.getItem('unreadSet')))
        };
    }

    function storeReadInfo(readInfo) {
        compactReadInfo(readInfo);
        window.localStorage.setItem('readThreshold', readInfo.readThreshold);
        window.localStorage.setItem('readSet', JSON.stringify(Array.from(readInfo.readSet)));
        window.localStorage.setItem('unreadSet', JSON.stringify(Array.from(readInfo.unreadSet)));
    }

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

        function storeWorking() {
            readInfo.readThreshold = working.readThreshold;
            readInfo.readSet = new Set(working.readSet);
            readInfo.unreadSet = new Set(working.unreadSet);
        }

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

        function up(info) {
            var newT = info.readThreshold + 1;
            if(info.readSet.has(info.readThreshold)) {
                info.readSet.delete(info.readThreshold);
            } else {
                info.unreadSet.add(info.readThreshold);
            }
            info.readThreshold = newT;
        }

        while(working.readThreshold != low) {
            down(working);
        }

        var best = working.readSet.size + working.unreadSet.size;
        storeWorking();
        while(working.readThreshold != high) {
            up(working);
            if(working.readSet.size + working.unreadSet.size <= best) {
                best = working.readSet.size + working.unreadSet.size;
                storeWorking();
            }
        }
    }

    function markAsRead(readInfo, id) {
        var id = parseInt(id);
        readInfo.readSet.add(id);
        readInfo.unreadSet.delete(id);
    }

    function markAsUnread(readInfo, id) {
        var id = parseInt(id);
        readInfo.readSet.delete(id);
        readInfo.unreadSet.add(id);
    }

    function markAllAsRead(readInfo, upto) {
        readInfo.readSet.clear();
        readInfo.unreadSet.clear();
        readInfo.readThreshold = upto + 1;
    }

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

    function isUnread(readInfo, id) {
        return !isRead(readInfo, id);
    }

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
            if(isUnread(readInfo, el.dataset.item)) {
                el.classList.add('item--unread');
            }
        });
    });

}();
