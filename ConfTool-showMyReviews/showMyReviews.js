var elements = document.querySelectorAll('div[align="left"]');
for (let el of elements) {
  let reviewLink = el.querySelector('a[href*="?page=reviewDetailsPC"]');
  if (!reviewLink) continue;
  if (!el.dataset.score) {
    appendReview(el, reviewLink.href);
  }
}

var nodeList = Array.prototype.slice.call(elements);
nodeList.sort(function (a, b) {
  return a.dataset.score > b.dataset.score ? 1 : -1;
});

var anchor = document.getElementById("ctform_reviewfilter");
for (let node of nodeList) {
  node.setAttribute("style", "padding-bottom: 32px;");
  insertAfter(node, anchor);
}

function appendReview(node, url) {
  var request = new XMLHttpRequest();
  request.open("GET", url, true);
  request.responseType = "document";
  request.onreadystatechange = function(e) {
    if (request.readyState === 4) {
      if (request.status === 200) {
        let reviewDoc = request.response;
        let reviewValues = reviewDoc.querySelector("div.infoview_body>table");
        if (reviewValues) {
          let grandparent = reviewValues.parentNode.parentNode;
          let reviewComments = grandparent;
          for (let i = 0; i < 5; i++) {
            reviewComments = reviewComments.nextSibling;
            if (reviewComments.textContent.trim() != "") {
              break;
            }
          }
          node.appendChild(reviewComments);
          node.appendChild(reviewValues);
          let score = reviewValues.querySelector("td:last-child span:last-child").textContent;
          if (score) {
            score = parseFloat(score);
            node.dataset.score = score;
          }
        }
      } else {
        console.error(request.status, request.statusText);
      }
    }
  };
  request.onerror = function(e) {
    console.error(request.status, request.statusText);
  };
  request.send(null);

}

function insertAfter(newNode, existingNode) {
  existingNode.parentNode.insertBefore(newNode, existingNode.nextSibling);
}
