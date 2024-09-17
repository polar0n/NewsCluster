let urls = new Array();
document.getElementsByClassName('sitemap-entry')[1]
    .childNodes[0].childNodes
    .forEach(function (list_item) {
        urls.push(list_item.lastChild.lastChild.href);
    });
console.log(urls);
