/* Focus and background management for explicitly opened, possibly nested dialogs. */
(function () {
  'use strict';
  var stack = [];
  function controls(element) {
    return Array.from(element.querySelectorAll('a[href],button,input:not([type="hidden"]),select,textarea,[tabindex]')).filter(function(item) {
      return !item.disabled && item.tabIndex >= 0 && item.getClientRects().length && !item.closest('[inert]');
    });
  }
  window.DialogFocus = {
    open: function(element, onClose, initialFocus) {
      if (stack.some(function(entry) { return entry.element === element; })) return;
      var entry = {element:element, close:onClose, trigger:document.activeElement, inert:[]};
      entry.inert.push([element, element.inert]);
      element.inert = false;
      for (var branch = element; branch && branch !== document.body; branch = branch.parentElement) {
        Array.from(branch.parentElement.children).forEach(function(sibling) {
          if (sibling === branch || sibling.id === 'toast-container' || ['SCRIPT','STYLE','LINK'].includes(sibling.tagName)) return;
          entry.inert.push([sibling, sibling.inert]); sibling.inert = true;
        });
      }
      stack.push(entry);
      element.classList.add('dialog-focus-open');
      (initialFocus || controls(element)[0] || element).focus();
    },
    close: function(element) {
      var entry = stack[stack.length - 1];
      if (!entry || entry.element !== element) return;
      stack.pop(); element.classList.remove('dialog-focus-open');
      entry.inert.forEach(function(value) { value[0].inert = value[1]; });
      if (entry.trigger && entry.trigger.isConnected) entry.trigger.focus();
    }
  };
  document.addEventListener('keydown', function(event) {
    var entry = stack[stack.length - 1];
    if (!entry) return;
    if (event.key === 'Escape') {
      event.preventDefault(); event.stopImmediatePropagation(); entry.close();
    } else if (event.key === 'Tab') {
      var items = controls(entry.element), first = items[0], last = items[items.length - 1];
      if (!first) { event.preventDefault(); entry.element.focus(); }
      else if (event.shiftKey && (document.activeElement === first || !entry.element.contains(document.activeElement))) { event.preventDefault(); last.focus(); }
      else if (!event.shiftKey && (document.activeElement === last || !entry.element.contains(document.activeElement))) { event.preventDefault(); first.focus(); }
    }
  }, true);
})();
