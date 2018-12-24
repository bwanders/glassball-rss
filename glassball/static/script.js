document.addEventListener('DOMContentLoaded', function() {

    document.querySelectorAll('.selector.item').forEach(function(el) {
        el.addEventListener('click', function() {
            document.querySelectorAll('.selector.item').forEach(function(el) {
                el.classList.remove('selector--selected');
            })
            el.classList.add('selector--selected');
            var itemUrl = el.dataset.item + '.html';
            document.querySelector('#item-view').src = itemUrl;
        });
    });

});
