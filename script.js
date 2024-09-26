let articles = new Array();
document.getElementsByClassName('sitemap-entry')[1]
    .childNodes[0].childNodes
    .forEach(function (list_item) {
        let article = new Array();
        article.push(list_item.firstChild.textContent);
        let el = list_item.lastChild.lastChild;
        article.push(el.text);
        article.push(el.href);
        articles.push(article);
    });
console.log(articles);
