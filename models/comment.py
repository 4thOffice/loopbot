class comment:
	sender = ""
	commentQuotedID = ""
	datetime = ""
	message = ""
	id = ""

	def __init__(self, id, sender, commentQuotedID, datetime, message):
		self.id = id
		self.sender = sender
		self.commentQuotedID = commentQuotedID
		self.datetime = datetime
		self.message = message