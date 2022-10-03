let stopper = false;
function stop(e){
	stopper = true;
}

var finishButton = document.querySelectorAll('[mattooltip="Download as SVG"]')[0];
finishButton.classList.remove('mat-button-disabled');

var new_element = finishButton.cloneNode(true);
finishButton.parentNode.replaceChild(new_element, finishButton);

new_element.addEventListener("click", stop);