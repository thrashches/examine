$('#delete-user-modal').on('show.bs.modal', function (event) {
    let url = event.relatedTarget.dataset.url; // Button that triggered the modal
    let form = this.querySelector('form');
    form.action = url;
    let userName = event.relatedTarget.closest('tr').querySelector('.user-name').textContent;
    this.querySelector('#user-name').textContent = userName;
})
  