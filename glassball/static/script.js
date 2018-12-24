document.addEventListener('DOMContentLoaded', function() {

    function items() {
        return document.querySelectorAll('.selector.item');
    }

    function filters() {
        return document.querySelectorAll('.selector.filter');
    }

    function uiSelect(collection, entry) {
        collection().forEach(function(el) {
            el.classList.remove('selector--selected');
        })
        entry.classList.add('selector--selected');
    }

    items().forEach(function(el) {
        el.addEventListener('click', function() {
            // Update UI for newly selected item
            uiSelect(items, el);

            // Navigate item viewer to item page
            var itemUrl = el.dataset.item + '.html';
            document.querySelector('#item-view').src = itemUrl;
        });
    });


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
        }
    }

    filters().forEach(function(el) {
        el.addEventListener('click', function() {
            // Update UI for newly selected filter
            uiSelect(filters, el);

            // Filter item list
            filterTypes[el.dataset.filterType](el.dataset);
        });
    });

});
